<template>
  <div class="login">
    <div class="login__aside">
      <div class="login__brand">
        <span class="login__logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2.6c3.3 4.3 5.7 7.3 5.7 10.1a5.7 5.7 0 0 1-11.4 0C6.3 9.9 8.7 6.9 12 2.6z" />
            <path d="M3 20.2c1.9 1.1 3.8 1.1 5.7 0 1.9-1.1 3.8-1.1 5.7 0 1.9 1.1 3.8 1.1 5.7 0" />
          </svg>
        </span>
        <span class="login__brand-name">智慧泳池 <i>/</i> 溺水实时防护</span>
      </div>

      <div class="login__pitch">
        <span class="login__eyebrow">SMARTPOOL · 实时防护</span>
        <h1>让每一次异常停留<br />都被及时看见</h1>
        <p>基于 Mamba-YOLO 的池面目标监测、风险分级与联动告警，为场馆提供可回溯的安全闭环。</p>
        <ul>
          <li><i />实时风险识别与分级预警</li>
          <li><i />分区电子围栏与轨迹回溯</li>
          <li><i />设备、水质与算力统一观测</li>
        </ul>
      </div>

      <div class="login__foot">演示环境 · 模型占位 · 数据全部合成，不代表真实场馆</div>
    </div>

    <div class="login__main">
      <div class="login__card">
        <div class="login__card-head">
          <h2>登录控制台</h2>
          <p>使用演示账号进入系统</p>
        </div>

        <el-form :model="form" label-position="top" @submit.prevent="submit">
          <el-form-item label="账号">
            <el-input v-model="form.username" size="large" placeholder="lifeguard / manager / sysadmin / demo" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" size="large" show-password @keyup.enter="submit" />
          </el-form-item>
          <el-button type="primary" size="large" class="login__submit" :loading="loading" @click="submit">
            登录
          </el-button>
        </el-form>

        <div class="login__hint">
          <div>演示账号：<b>lifeguard</b> / <b>manager</b> / <b>sysadmin</b> / <b>demo</b></div>
          <div>统一口令：<b>demo1234</b></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const store = useUserStore()

const form = reactive({ username: 'manager', password: 'demo1234' })
const loading = ref(false)

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号与密码')
    return
  }
  loading.value = true
  try {
    await store.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/monitor'
    router.push(redirect)
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  position: relative;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  background: var(--card);
  overflow: hidden;
}

.login::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(680px 340px at 20% 0%, rgba(67, 185, 245, .10), transparent 72%);
}

.login::after {
  content: "";
  position: absolute;
  inset: 0 50% 0 0;
  pointer-events: none;
  background-image: radial-gradient(rgba(125, 195, 240, .16) 1px, transparent 1px);
  background-size: 22px 22px;
  mask-image: radial-gradient(760px 500px at 28% 8%, #000 0%, transparent 76%);
}

.login__aside {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  padding: 34px 48px;
  background: linear-gradient(165deg, #102439 0%, #0e1b28 62%, #0d1621 100%);
  border-right: 1px solid var(--line);
}

.login__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--ink);
}

.login__brand i {
  font-style: normal;
  color: var(--brand-bright);
  margin: 0 2px;
}

.login__logo {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-lg);
  background: var(--brand);
  color: #f0f7ff;
  box-shadow: 0 4px 12px var(--brand-glow);
}

.login__logo svg {
  width: 21px;
  height: 21px;
}

.login__pitch {
  margin: auto 0;
  max-width: 480px;
}

.login__eyebrow {
  display: inline-block;
  font-size: 11.5px;
  font-weight: 650;
  letter-spacing: .12em;
  color: var(--brand-deep);
}

.login__pitch h1 {
  margin: 18px 0 16px;
  font-size: clamp(30px, 3.2vw, 42px);
  line-height: 1.32;
  font-weight: 680;
  letter-spacing: -0.03em;
  color: var(--ink);
}

.login__pitch p {
  margin: 0;
  max-width: 420px;
  font-size: 13.5px;
  line-height: 1.9;
  color: var(--ink-3);
}

.login__pitch ul {
  list-style: none;
  margin: 30px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 13px;
  color: var(--ink-2);
}

.login__pitch li {
  display: flex;
  align-items: center;
  gap: 10px;
}

.login__pitch li i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 4px rgba(67, 185, 245, .12);
}

.login__foot {
  font-size: 11.5px;
  color: var(--ink-4);
}

.login__main {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.login__card {
  width: 100%;
  max-width: 380px;
  padding: 32px;
  border: 1px solid var(--line);
  border-radius: var(--r-xl);
  background: var(--card);
  box-shadow: var(--shadow-2);
}

.login__card-head h2 {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.login__card-head p {
  margin: 0 0 26px;
  font-size: 12.5px;
  color: var(--ink-4);
}

.login__submit {
  width: 100%;
  margin-top: 10px;
}

.login__hint {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line-soft);
  font-size: 12px;
  line-height: 1.9;
  color: var(--ink-4);
}

.login__hint b {
  color: var(--ink-2);
  font-weight: 600;
}

@media (max-width: 900px) {
  .login {
    grid-template-columns: 1fr;
  }
  .login__aside {
    display: none;
  }
}
</style>
