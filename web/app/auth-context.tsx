'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/router';
import { STORAGE_USERINFO_KEY } from '@/utils/constants/storage';

interface User {
  username: string;
  [key: string]: any;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; message?: string }>;
  logout: () => void;
  isAuthenticated: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // 初始化时检查登录状态
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('access_token');
      const userInfo = localStorage.getItem('user_info');
      
      if (token && userInfo) {
        try {
          const parsedUser = JSON.parse(userInfo);
          setUser(parsedUser);
          // 同步到 STORAGE_USERINFO_KEY
          localStorage.setItem(STORAGE_USERINFO_KEY, JSON.stringify(parsedUser));
          console.log('从 localStorage 恢复登录状态:', parsedUser.username);
        } catch (error) {
          console.error('Failed to parse user info:', error);
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_info');
          localStorage.removeItem(STORAGE_USERINFO_KEY);
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      // Use API_BASE_URL from environment or default to backend address
      const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:5670';
      
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const result = await response.json();

      if (result.success) {
        localStorage.setItem('access_token', result.token);
        localStorage.setItem('user_info', JSON.stringify(result.user));
        // 同时保存到 STORAGE_USERINFO_KEY，以便 UserBar 组件可以读取
        localStorage.setItem(STORAGE_USERINFO_KEY, JSON.stringify(result.user));
        setUser(result.user);
        return { success: true };
      } else {
        return { success: false, message: result.message || '登录失败' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, message: '登录失败，请稍后重试' };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem(STORAGE_USERINFO_KEY);
    setUser(null);
    router.push('/login');
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
