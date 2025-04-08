<template>
  <div class="home-view">
    <!-- 公共信息展示 -->
    <section class="hero-section">
      <img :src="logo" alt="Bank Logo" class="logo" />
      <h1>{{ $t('secure_banking_solutions') }}</h1>
      <p>{{ $t('home_subtitle') }}</p>
    </section>

    <!-- 安全入口 -->
    <div class="action-cards">
      <el-card 
        v-for="card in actionCards" 
        :key="card.title" 
        :class="['action-card', card.variant]"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <el-icon><component :is="card.icon" /></el-icon>
            <span>{{ $t(card.title) }}</span>
          </div>
        </template>
        <p>{{ $t(card.description) }}</p>
        <el-button 
          :type="card.buttonType" 
          @click="handleCardAction(card.action)"
          v-if="card.showButton"
        >
          {{ $t(card.buttonText) }}
        </el-button>
      </el-card>
    </div>

    <!-- 安全提示 -->
    <div class="security-tips">
      <h3>{{ $t('security_reminders') }}</h3>
      <ul>
        <li v-for="tip in securityTips" :key="tip">
          <el-icon><WarningFilled /></el-icon>
          {{ $t(tip) }}
        </li>
      </ul>
    </div>

    <!-- 系统公告 -->
    <div class="announcements" v-if="announcements.length">
      <h3>{{ $t('system_announcements') }}</h3>
      <el-carousel :interval="5000" type="card" height="200px">
        <el-carousel-item v-for="item in announcements" :key="item.id">
          <h4>{{ item.title }}</h4>
          <p>{{ item.content }}</p>
          <small>{{ formatDate(item.date) }}</small>
        </el-carousel-item>
      </el-carousel>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import logo from '@/assets/logo.svg';
import { 
  UserFilled,
  Money,
  Document,
  WarningFilled,
  ChatLineSquare
} from '@element-plus/icons-vue';
import api from '@/services/api';

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();

// 动态卡片配置
const actionCards = computed(() => [
  {
    title: 'login',
    description: 'login_description',
    icon: UserFilled,
    variant: 'primary',
    buttonType: 'primary',
    buttonText: 'login',
    action: 'login',
    showButton: !authStore.isAuthenticated
  },
  {
    title: 'create_account',
    description: 'create_account_description',
    icon: Document,
    variant: 'success',
    buttonType: 'success',
    buttonText: 'register',
    action: 'register',
    showButton: !authStore.isAuthenticated
  },
  {
    title: 'quick_transfer',
    description: 'transfer_funds_quickly',
    icon: Money,
    variant: 'warning',
    buttonType: 'warning',
    buttonText: 'transfer_now',
    action: 'transfer',
    showButton: authStore.isAuthenticated
  },
  {
    title: 'support',
    description: 'get_technical_support',
    icon: ChatLineSquare,
    variant: 'info',
    buttonType: 'info',
    buttonText: 'contact_us',
    action: 'support',
    showButton: true
  }
]);

// 安全提示内容
const securityTips = [
  'never_share_credentials',
  'verify_https',
  'report_suspicious_activity',
  'update_password_regularly'
];

// 系统公告
const announcements = ref([
  {
    id: 1,
    title: 'System Maintenance',
    content: 'Scheduled maintenance on 2023-12-31 23:00-02:00',
    date: '2023-12-25'
  }
]);

// 事件处理
const handleCardAction = (action: string) => {
  switch(action) {
    case 'login':
      router.push('/login');
      break;
    case 'register':
      router.push('/register');
      break;
    case 'transfer':
      router.push('/dashboard');
      break;
    case 'support':
      window.open('mailto:support@bank.example.com');
      break;
  }
};

// 日期格式化
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString();
};

// 获取实时公告
onMounted(async () => {
  try {
    const res = await api.get('/api/public/announcements');
    announcements.value = res.data;
  } catch (error) {
    console.error('Failed to fetch announcements:', error);
  }
});
</script>

<style scoped lang="scss">
.home-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.hero-section {
  text-align: center;
  margin-bottom: 40px;
  .logo {
    width: 150px;
    height: auto;
  }
  h1 {
    color: #2c3e50;
    margin: 20px 0;
  }
  p {
    color: #666;
    font-size: 1.2em;
  }
}

.action-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
  .action-card {
    transition: transform 0.2s;
    &:hover {
      transform: translateY(-5px);
    }
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
    }
  }
}

.security-tips {
  background: #fff3e0;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 40px;
  ul {
    list-style: none;
    padding: 0;
    li {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 10px 0;
      color: #e67e22;
    }
  }
}

.announcements {
  .el-carousel__item {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 4px;
    h4 {
      color: #34495e;
      margin-bottom: 15px;
    }
    p {
      color: #7f8c8d;
      margin-bottom: 10px;
    }
    small {
      color: #95a5a6;
      display: block;
      text-align: right;
    }
  }
}
</style>