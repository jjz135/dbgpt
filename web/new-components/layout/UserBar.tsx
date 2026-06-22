import { UserInfoResponse } from '@/types/userinfo';
import { STATIC_DISPLAY_NAME, STORAGE_USERINFO_KEY } from '@/utils/constants/index';
import { Avatar, Dropdown, MenuProps, Modal, Form, Input, Button, message, Divider } from 'antd';
import { UserOutlined, EditOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import cls from 'classnames';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

function UserBar({ onlyAvatar = false }) {
  const router = useRouter();
  const [userInfo, setUserInfo] = useState<UserInfoResponse>();
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [editForm] = Form.useForm();
  useEffect(() => {
    try {
      const user = JSON.parse(localStorage.getItem(STORAGE_USERINFO_KEY) ?? '');
      setUserInfo(user);
    } catch {
      return undefined;
    }
  }, []);

  // 登出功能
  const handleLogout = () => {
    Modal.confirm({
      title: '确认登出',
      content: '您确定要退出登录吗？',
      okText: '确认',
      cancelText: '取消',
      onOk: () => {
        localStorage.removeItem(STORAGE_USERINFO_KEY);
        message.success('登出成功');
        router.push('/login');
      },
    });
  };

  // 打开编辑用户信息弹窗
  const handleEditProfile = () => {
    editForm.setFieldsValue({
      nick_name: userInfo?.nick_name || '',
      email: userInfo?.email || '',
      phone: userInfo?.phone || '',
    });
    setIsEditModalVisible(true);
  };

  // 保存用户信息
  const handleSaveProfile = async () => {
    try {
      const values = await editForm.validateFields();
      
      // 更新本地存储的用户信息
      const updatedUserInfo = {
        ...userInfo,
        ...values,
      };
      
      localStorage.setItem(STORAGE_USERINFO_KEY, JSON.stringify(updatedUserInfo));
      setUserInfo(updatedUserInfo);
      message.success('用户信息更新成功');
      setIsEditModalVisible(false);
    } catch (error) {
      message.error('更新失败，请重试');
    }
  };

  // 用户菜单配置
  const menuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
      onClick: handleEditProfile,
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '账号设置',
      onClick: () => {
        message.info('账号设置功能开发中...');
      },
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: handleLogout,
    },
  ];

  return (
    <>
      <div className='flex flex-1 items-center justify-center'>
        <Dropdown 
          menu={{ items: menuItems }} 
          placement="topLeft"
          trigger={['click']}
        >
          <div
            className={cls('flex items-center group w-full cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg p-2 transition-all', {
              'justify-center': onlyAvatar,
              'justify-between': !onlyAvatar,
            })}
          >
            <span className='flex gap-2 items-center'>
              <Avatar src={userInfo?.avatar_url} className='bg-gradient-to-tr from-[#31afff] to-[#1677ff] cursor-pointer'>
                {userInfo?.nick_name?.charAt(0) || userInfo?.username?.charAt(0) || 'U'}
              </Avatar>
              <span
                className={cls('text-sm font-medium', {
                  hidden: onlyAvatar,
                })}
              >
                {userInfo?.nick_name || userInfo?.username || STATIC_DISPLAY_NAME}
              </span>
            </span>
          </div>
        </Dropdown>
      </div>

      {/* 编辑用户信息弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <EditOutlined />
            <span>编辑个人信息</span>
          </div>
        }
        open={isEditModalVisible}
        onCancel={() => setIsEditModalVisible(false)}
        footer={null}
        width={500}
      >
        <Divider />
        <Form
          form={editForm}
          layout="vertical"
          initialValues={{
            nick_name: userInfo?.nick_name || '',
            email: userInfo?.email || '',
            phone: userInfo?.phone || '',
          }}
          onFinish={handleSaveProfile}
          autoComplete="off"
        >
          <Form.Item
            label="昵称"
            name="nick_name"
            rules={[
              { required: true, message: '请输入昵称' },
              { min: 2, message: '昵称至少2个字符' },
              { max: 20, message: '昵称最多20个字符' },
            ]}
          >
            <Input placeholder="请输入昵称" />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          <Form.Item
            label="手机号"
            name="phone"
            rules={[
              { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' },
            ]}
          >
            <Input placeholder="请输入手机号" />
          </Form.Item>

          <Form.Item className="mb-0 flex justify-end gap-2">
            <Button onClick={() => setIsEditModalVisible(false)}>
              取消
            </Button>
            <Button type="primary" htmlType="submit">
              保存
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

export default UserBar;
