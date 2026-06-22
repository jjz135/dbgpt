'use client';

import { useState, useContext, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { AuthContext } from '@/app/auth-context';

interface FormValues {
    username: string;
    password: string;
    email?: string;
    confirmPassword?: string;
}

export default function LoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [mounted, setMounted] = useState(false);
    const [isRegister, setIsRegister] = useState(false); // 控制登录与注册状态切换
    const [form] = Form.useForm();
    const authContext = useContext(AuthContext);

    useEffect(() => {
        setMounted(true);
    }, []);

    // 切换表单时清空输入
    const toggleMode = () => {
        setIsRegister(!isRegister);
        form.resetFields();
    };

    if (!mounted) return null;

    // 提交表单处理（登录 / 注册）
    const handleSubmit = async (values: FormValues) => {
        if (!authContext) {
            message.error('认证上下文未初始化');
            return;
        }

        setLoading(true);
        try {
            if (isRegister) {
                // --- 注册逻辑 ---
                // 提示：此处需要根据你的 AuthContext 实际是否有 register 方法来调整
                // @ts-expect-error - register 方法可能不存在
                if (authContext.register) {
                    // @ts-expect-error - register 方法可能不存在
                    const result = await authContext.register(values.username, values.password, values.email);
                    if (result.success) {
                        message.success('注册成功！请登录');
                        setIsRegister(false);
                        form.resetFields();
                    } else {
                        message.error(result.message || '注册失败');
                    }
                } else {
                    // 模拟注册成功
                    setTimeout(() => {
                        message.success('注册成功！（当前为模拟前端响应）');
                        setIsRegister(false);
                        form.resetFields();
                    }, 1000);
                }
            } else {
                // --- 登录逻辑 ---
                const result = await authContext.login(values.username, values.password);
                if (result.success) {
                    message.success('登录成功!');
                    window.location.href = 'http://localhost:5670/';
                } else {
                    message.error(result.message || '登录失败');
                }
            }
        } catch (error) {
            console.error('Submit error:', error);
            message.error('操作失败，请稍后重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            // 使用科技感背景图片
            backgroundImage: 'url(/loginhero.png)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            position: 'relative',
            padding: '20px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }}>
            {/* 添加半透明遮罩层，让表单更清晰 */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.3)',
                zIndex: 0
            }} />

            <div style={{
                width: '100%',
                maxWidth: '420px',
                background: 'rgba(255, 255, 255, 0.96)',
                borderRadius: '16px',
                boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
                padding: '40px 32px',
                transition: 'all 0.3s ease',
                position: 'relative',
                zIndex: 1
            }}>
                {/* 头部标题区 */}
                <div style={{ textAlign: 'center', marginBottom: '36px' }}>
                    <h1 style={{
                        fontSize: '26px',
                        fontWeight: 700,
                        letterSpacing: '1px',
                        background: 'linear-gradient(90deg, #1890ff, #722ed1)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        margin: '0 0 8px 0'
                    }}>
                        JQAI智能中枢平台
                    </h1>
                    <p style={{ color: '#8c8c8c', fontSize: '14px', margin: 0 }}>
                        {isRegister ? '创建您的专属平台账户' : '欢迎回来，请登录您的账户'}
                    </p>
                </div>

                {/* 表单区 */}
                <Form
                    form={form}
                    name="auth_form"
                    onFinish={handleSubmit}
                    size="large"
                    layout="vertical"
                    requiredMark={false}
                >
                    {/* 用户名 */}
                    <Form.Item
                        name="username"
                        rules={[
                            { required: true, message: '请输入用户名!' },
                            { min: 3, message: '用户名至少3个字符!' }
                        ]}
                    >
                        <Input
                            prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
                            placeholder="用户名"
                            style={{ borderRadius: '8px' }}
                        />
                    </Form.Item>

                    {/* 邮箱（仅在注册时显示） */}
                    {isRegister && (
                        <Form.Item
                            name="email"
                            rules={[
                                { required: true, message: '请输入邮箱!' },
                                { type: 'email', message: '请输入有效的邮箱格式!' }
                            ]}
                        >
                            <Input
                                prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
                                placeholder="电子邮箱"
                                style={{ borderRadius: '8px' }}
                            />
                        </Form.Item>
                    )}

                    {/* 密码 */}
                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: '请输入密码!' }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                            placeholder="密码"
                            style={{ borderRadius: '8px' }}
                        />
                    </Form.Item>

                    {/* 确认密码（仅在注册时显示） */}
                    {isRegister && (
                        <Form.Item
                            name="confirmPassword"
                            dependencies={['password']}
                            rules={[
                                { required: true, message: '请再次输入密码确认!' },
                                ({ getFieldValue }) => ({
                                    validator(_, value) {
                                        if (!value || getFieldValue('password') === value) {
                                            return Promise.resolve();
                                        }
                                        return Promise.reject(new Error('两次输入的密码不一致!'));
                                    },
                                }),
                            ]}
                        >
                            <Input.Password
                                prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                                placeholder="确认密码"
                                style={{ borderRadius: '8px' }}
                            />
                        </Form.Item>
                    )}

                    {/* 提交按钮 */}
                    <Form.Item style={{ marginTop: '30px', marginBottom: '16px' }}>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            block
                            icon={<ArrowRightOutlined />}
                            style={{
                                height: '46px',
                                fontSize: '15px',
                                fontWeight: 600,
                                borderRadius: '8px',
                                background: 'linear-gradient(90deg, #1890ff 0%, #40a9ff 100%)',
                                border: 'none',
                                boxShadow: '0 4px 12px rgba(24, 144, 255, 0.3)'
                            }}
                        >
                            {isRegister ? '立即注册' : '登 录'}
                        </Button>
                    </Form.Item>
                </Form>

                {/* 底部切换触发器 */}
                <div style={{
                    textAlign: 'center',
                    fontSize: '14px',
                    color: '#666',
                    marginTop: '24px'
                }}>
                    {isRegister ? (
                        <span>
              已有账号？{' '}
                            <a onClick={toggleMode} style={{ color: '#1890ff', fontWeight: 500 }}>
                立即登录
              </a>
            </span>
                    ) : (
                        <span>
              还没有账号？{' '}
                            <a onClick={toggleMode} style={{ color: '#1890ff', fontWeight: 500 }}>
                注册新用户
              </a>
            </span>
                    )}
                </div>
            </div>
        </div>
    );
}
