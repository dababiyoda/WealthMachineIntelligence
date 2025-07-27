"""
Custom middleware for security, logging, and monitoring
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.logging_config import logger

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with structured logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Log request
        logger.info("Request started",
                   request_id=request_id,
                   method=request.method,
                   path=request.url.path,
                   query_params=dict(request.query_params),
                   client_ip=request.client.host if request.client else None,
                   user_agent=request.headers.get("user-agent"))
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info("Request completed",
                       request_id=request_id,
                       status_code=response.status_code,
                       duration=duration)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error("Request failed",
                        request_id=request_id,
                        error=str(e),
                        duration=duration)
            
            raise

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        self.clients = {
            ip: requests for ip, requests in self.clients.items()
            if any(req_time > current_time - self.period for req_time in requests)
        }
        
        # Check rate limit
        if client_ip in self.clients:
            recent_requests = [
                req_time for req_time in self.clients[client_ip]
                if req_time > current_time - self.period
            ]
            if len(recent_requests) >= self.calls:
                logger.warning("Rate limit exceeded", client_ip=client_ip)
                return Response(
                    content="Rate limit exceeded",
                    status_code=429,
                    headers={"Retry-After": str(self.period)}
                )
            self.clients[client_ip] = recent_requests + [current_time]
        else:
            self.clients[client_ip] = [current_time]
        
        return await call_next(request)