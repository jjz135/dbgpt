"""Simple authentication service for DB-GPT web UI"""
import base64
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None


# Create a simple router for auth endpoints
router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# Simple in-memory user database (for demo purposes)
# In production, this should be replaced with a real database
USERS = {
    "admin": {
        "username": "admin",
        "password": base64.b64encode("admin123".encode()).decode(),  # Base64 encoded
        "user_id": "001",
        "real_name": "Administrator",
        "role": "admin",
        "nick_name": "Admin"
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return base64.b64encode(plain_password.encode()).decode() == hashed_password


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    User login endpoint
    
    Args:
        request: Login request with username and password
        
    Returns:
        Login response with token and user info
    """
    username = request.username
    password = request.password
    
    # Check if user exists
    if username not in USERS:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "message": "用户名或密码错误"}
        )
    
    user = USERS[username]
    
    # Verify password
    if not verify_password(password, user["password"]):
        raise HTTPException(
            status_code=401,
            detail={"success": False, "message": "用户名或密码错误"}
        )
    
    # Generate a simple token (in production, use JWT or similar)
    token = base64.b64encode(f"{username}:{user['user_id']}".encode()).decode()
    
    # Return user info (without password)
    user_info = {
        "username": user["username"],
        "user_id": user["user_id"],
        "real_name": user["real_name"],
        "role": user["role"],
        "nick_name": user["nick_name"]
    }
    
    return LoginResponse(
        success=True,
        message="登录成功",
        token=token,
        user=user_info
    )


@router.get("/logout")
async def logout():
    """
    User logout endpoint
    
    Note: Since we're using localStorage on the client side,
    this endpoint is mainly for logging purposes.
    The actual logout happens on the client by clearing localStorage.
    """
    return {"success": True, "message": "登出成功"}


@router.get("/me")
async def get_current_user(token: str = None):
    """
    Get current user info
    
    Args:
        token: Authentication token from header or query param
        
    Returns:
        Current user info
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "message": "未登录"}
        )
    
    try:
        # Decode token
        decoded = base64.b64decode(token).decode()
        username, user_id = decoded.split(":")
        
        if username not in USERS:
            raise HTTPException(
                status_code=401,
                detail={"success": False, "message": "无效的token"}
            )
        
        user = USERS[username]
        user_info = {
            "username": user["username"],
            "user_id": user["user_id"],
            "real_name": user["real_name"],
            "role": user["role"],
            "nick_name": user["nick_name"]
        }
        
        return {"success": True, "user": user_info}
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "message": f"验证失败: {str(e)}"}
        )
