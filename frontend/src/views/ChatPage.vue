<template>
  <div class="grid">
    <section class="card">
      <h2 class="card-title">热门股票</h2>
      <div class="stock-list">
        <RouterLink
          v-for="item in watchlist"
          :key="item.symbol"
          class="stock-item"
          :to="`/stock/${item.symbol}`"
        >
          <strong>{{ item.name }} ({{ item.symbol }})</strong>
          <small>点击查看行情与走势图</small>
        </RouterLink>
      </div>
    </section>

    <section class="card chat-panel">
      <div class="message-list">
        <MessageItem
          v-for="(message, index) in chatStore.messages"
          :key="`${message.createdAt}-${index}`"
          :message="message"
        />
      </div>

      <ChatBox :loading="chatStore.loading" @submit="handleSubmit" />
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getWatchlist } from '../api/stock'
import { useChatStore } from '../store/chatStore'
import ChatBox from '../components/ChatBox.vue'
import MessageItem from '../components/MessageItem.vue'

const chatStore = useChatStore()
const watchlist = ref([])

async function handleSubmit(message) {
  await chatStore.ask(message)
}

onMounted(async () => {
  try {
    watchlist.value = await getWatchlist()
  } catch {
    watchlist.value = []
  }
})
</script>
