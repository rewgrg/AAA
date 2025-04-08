<template>
  <div class="login-form">
    <input v-model="username" placeholder="Username" type="text">
    <input v-model="password" placeholder="Password" type="password">
    <button @click="handleLogin">Login</button>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      username: '',
      password: ''
    }
  },
  methods: {
    async handleLogin() {
      try {
        const res = await axios.post('/api/auth/login', {
          username: this.username,
          password: this.password
        })
        localStorage.setItem('access_token', res.data.token)
        this.$router.push('/dashboard')
      } catch (error) {
        alert('Login failed')
      }
    }
  }
}
</script>