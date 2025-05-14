"""Utilities for secure code execution in a sandbox environment."""
import RestrictedPython
from RestrictedPython import compile_restricted, safe_globals
import psutil
import threading
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
import logging
from utils.logging_utils import setup_json_logging

# Configure logging
logger = setup_json_logging("sandbox")

class ResourceLimitExceeded(Exception):
    """Exception raised when resource limits are exceeded."""
    pass

class SecurityViolation(Exception):
    """Exception raised when a security violation is detected."""
    pass

class ResourceMonitor:
    """Monitor and limit resource usage during code execution."""
    
    def __init__(self, max_memory_mb: float = 500, max_cpu_percent: float = 50):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_cpu_percent = max_cpu_percent
        self.should_stop = False
        self._monitor_thread = None
        
    def start_monitoring(self):
        """Start the resource monitoring thread."""
        self.should_stop = False
        self._monitor_thread = threading.Thread(target=self._monitor_resources)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop the resource monitoring thread."""
        self.should_stop = True
        if self._monitor_thread:
            self._monitor_thread.join()
            
    def _monitor_resources(self):
        """Monitor memory and CPU usage."""
        process = psutil.Process()
        while not self.should_stop:
            try:
                # Check memory usage
                memory_info = process.memory_info()
                if memory_info.rss > self.max_memory_bytes:
                    logger.error("Memory limit exceeded", extra={
                        "current_memory": memory_info.rss,
                        "limit": self.max_memory_bytes
                    })
                    raise ResourceLimitExceeded("Memory usage exceeded limit")
                
                # Check CPU usage
                cpu_percent = process.cpu_percent()
                if cpu_percent > self.max_cpu_percent:
                    logger.error("CPU limit exceeded", extra={
                        "cpu_percent": cpu_percent,
                        "limit": self.max_cpu_percent
                    })
                    raise ResourceLimitExceeded("CPU usage exceeded limit")
                
                time.sleep(0.1)  # Check every 100ms
            except psutil.NoSuchProcess:
                break

def get_safe_globals() -> Dict[str, Any]:
    """
    Get a dictionary of safe globals for restricted execution.
    This includes basic Python builtins and safe mathematical operations.
    """
    safe_builtins = RestrictedPython.safe_builtins.copy()
    
    # Add safe mathematical operations
    safe_math = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'len': len,
    }
    
    return {
        '__builtins__': safe_builtins,
        'math': safe_math,
    }

def sandbox_decorator(func: Callable) -> Callable:
    """
    Decorator to run a function in the sandbox environment with resource monitoring.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = ResourceMonitor()
        try:
            monitor.start_monitoring()
            result = func(*args, **kwargs)
            return result
        finally:
            monitor.stop_monitoring()
    return wrapper

class CodeValidator:
    """Validate code before execution in the sandbox."""
    
    FORBIDDEN_TERMS = [
        'import', 'exec', 'eval', 'open',
        'file', 'system', 'os.', 'subprocess',
        '__import__', 'breakpoint', 'globals',
    ]
    
    @classmethod
    def validate_code(cls, code: str) -> bool:
        """
        Validate code for potential security issues.
        Returns True if code is safe, raises SecurityViolation otherwise.
        """
        # Check for forbidden terms
        for term in cls.FORBIDDEN_TERMS:
            if term in code:
                raise SecurityViolation(f"Forbidden term found in code: {term}")
        
        try:
            # Try to compile the code to check for syntax errors
            compile_restricted(code, '<string>', 'exec')
            return True
        except Exception as e:
            raise SecurityViolation(f"Code validation failed: {str(e)}")

def execute_in_sandbox(code: str, globals_dict: Optional[Dict[str, Any]] = None) -> Any:
    """
    Execute code in a secure sandbox environment.
    
    Args:
        code: The Python code to execute
        globals_dict: Optional dictionary of additional globals
        
    Returns:
        The result of the code execution
        
    Raises:
        SecurityViolation: If the code fails validation
        ResourceLimitExceeded: If resource limits are exceeded
        Exception: For other execution errors
    """
    try:
        # Validate code
        CodeValidator.validate_code(code)
        
        # Prepare globals
        execution_globals = get_safe_globals()
        if globals_dict:
            execution_globals.update(globals_dict)
        
        # Compile and execute
        byte_code = compile_restricted(code, '<string>', 'exec')
        
        # Create a new dictionary for locals
        locals_dict = {}
        
        # Execute with resource monitoring
        monitor = ResourceMonitor()
        try:
            monitor.start_monitoring()
            exec(byte_code, execution_globals, locals_dict)
        finally:
            monitor.stop_monitoring()
        
        # Return the result if available
        if 'result' in locals_dict:
            return locals_dict['result']
        return None
        
    except Exception as e:
        logger.error("Sandbox execution failed", extra={
            "error": str(e),
            "code": code
        })
        raise 