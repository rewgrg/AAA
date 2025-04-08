<template>
  <div class="dashboard-container">
    <!-- 安全信息展示 -->
    <div v-if="user" class="user-info">
      <h3>{{ $t('welcome') }}, {{ user.username }}</h3>
      <security-badge :role="user.role" :mfa-enabled="user.mfaEnabled" />
    </div>

    <!-- 敏感操作区域 -->
    <div class="action-panel">
      <el-button 
        type="primary" 
        @click="showTransferDialog = true"
        v-has-permission="'transfer_funds'"
      >
        {{ $t('transfer_funds') }}
      </el-button>

      <el-button 
        v-if="isAdmin"
        type="warning"
        @click="showAuditLogs = true"
      >
        {{ $t('view_audit_logs') }}
      </el-button>
    </div>

    <!-- 账户信息 -->
    <div class="account-summary">
      <h4>{{ $t('account_balance') }}</h4>
      <el-skeleton :loading="loading" animated>
        <template #default>
          <div class="balance-display">
            {{ formattedBalance }}
            <el-tooltip effect="dark" :content="$t('balance_encrypted')" placement="top">
              <el-icon><Lock/></el-icon>
            </el-tooltip>
          </div>
        </template>
      </el-skeleton>
    </div>

    <!-- 近期交易记录 -->
    <div class="recent-transactions">
      <h4>{{ $t('recent_transactions') }}</h4>
      <el-table 
        :data="transactions" 
        stripe 
        :default-sort="{ prop: 'date', order: 'descending' }"
        v-loading="loading"
      >
        <el-table-column prop="date" :label="$t('date')" width="180" />
        <el-table-column prop="amount" :label="$t('amount')" width="120">
          <template #default="scope">
            <span :class="scope.row.type">{{ scope.row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="counterparty" :label="$t('counterparty')" />
        <el-table-column prop="status" :label="$t('status')" width="100">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 转账对话框 -->
    <el-dialog 
      v-model="showTransferDialog" 
      :title="$t('transfer_funds')"
      width="30%"
      :before-close="handleClose"
    >
      <el-form :model="transferForm" label-width="120px" :rules="transferRules">
        <el-form-item :label="$t('target_account')" prop="targetAccount">
          <el-input v-model="transferForm.targetAccount" type="number" />
        </el-form-item>
        <el-form-item :label="$t('amount')" prop="amount">
          <el-input v-model.number="transferForm.amount" type="number" />
        </el-form-item>
        <el-form-item v-if="requiresOTP" :label="$t('otp_code')" prop="otp">
          <el-input v-model="transferForm.otp" type="text" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTransferDialog = false">{{ $t('cancel') }}</el-button>
        <el-button 
          type="primary" 
          @click="submitTransfer"
          :loading="submitting"
        >
          {{ $t('confirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 审计日志抽屉 -->
    <el-drawer
      v-model="showAuditLogs"
      :title="$t('audit_logs')"
      size="50%"
    >
      <audit-log-list />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useTransactionStore } from '@/stores/transaction';
import { ElMessage } from 'element-plus';
import api from '@/services/api';
import { formatCurrency } from '@/utils/format';
import SecurityBadge from '@/components/SecurityBadge.vue';
import AuditLogList from '@/components/AuditLogList.vue';

const { t } = useI18n();
const authStore = useAuthStore();
const transactionStore = useTransactionStore();

// 用户权限判断
const isAdmin = computed(() => authStore.user?.role === 'admin');
const requiresOTP = computed(() => authStore.user?.mfaEnabled);

// 数据加载状态
const loading = ref(false);
const submitting = ref(false);
const showTransferDialog = ref(false);
const showAuditLogs = ref(false);

// 表单数据
const transferForm = ref({
  targetAccount: '',
  amount: 0,
  otp: ''
});

// 验证规则
const transferRules = {
  targetAccount: [
    { required: true, message: t('target_account_required'), trigger: 'blur' },
    { type: 'number', message: t('invalid_account_number'), trigger: 'blur' }
  ],
  amount: [
    { required: true, message: t('amount_required'), trigger: 'blur' },
    { type: 'number', min: 1, message: t('minimum_amount'), trigger: 'blur' }
  ],
  otp: [
    { required: requiresOTP, message: t('otp_required'), trigger: 'blur' },
    { len: 6, message: t('otp_length'), trigger: 'blur' }
  ]
};

// 获取账户信息
const fetchAccountData = async () => {
  try {
    loading.value = true;
    await transactionStore.fetchBalance();
    await transactionStore.fetchTransactions();
  } finally {
    loading.value = false;
  }
};

// 提交转账
const submitTransfer = async () => {
  try {
    submitting.value = true;
    await api.post('/api/data/transactions', {
      from_account: authStore.user?.accountId,
      to_account: transferForm.value.targetAccount,
      amount: transferForm.value.amount,
      otp: transferForm.value.otp
    });
    ElMessage.success(t('transfer_success'));
    showTransferDialog.value = false;
    await fetchAccountData(); // 刷新数据
  } catch (error) {
    ElMessage.error(error.response?.data?.error || t('transfer_failed'));
  } finally {
    submitting.value = false;
  }
};

// 生命周期钩子
onMounted(() => {
  fetchAccountData();
});
</script>

<style scoped lang="scss">
.dashboard-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.user-info {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.balance-display {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.recent-transactions {
  margin-top: 30px;
}

.transfer-out {
  color: #f56c6c;
}

.transfer-in {
  color: #67c23a;
}
</style>