<template>
  <div class="chat-box">
    <textarea
      v-model="draft"
      placeholder="请输入问题，例如：帮我分析恒瑞医药的研发管线、集采对某公司的影响、600519 今天行情"
      @keydown.enter.exact.prevent="submit"
    />
    <div style="display:flex;gap:8px;align-items:center;">
      <label class="upload-btn" title="上传年报/研报 PDF 到知识库">
        📄 上传PDF
        <input type="file" accept=".pdf" style="display:none" @change="uploadPdf" />
      </label>
      <button class="primary-btn" :disabled="disabled" @click="submit">
        {{ disabled ? '发送中' : '发送' }}
      </button>
    </div>
    <div v-if="uploadStatus" class="upload-status">{{ uploadStatus }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import request from '../api/request'

const emit = defineEmits(['submit'])
const props = defineProps({
  loading: { type: Boolean, default: false }
})

const draft = ref('')
const uploadStatus = ref('')
const disabled = computed(() => props.loading || !draft.value.trim())

function submit() {
  const message = draft.value.trim()
  if (!message || props.loading) return
  emit('submit', message)
  draft.value = ''
}

async function uploadPdf(e) {
  const file = e.target.files[0]
  if (!file) return
  uploadStatus.value = `正在上传 ${file.name}...`
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await request.post('/api/upload_pdf', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    uploadStatus.value = res.message || '上传成功'
  } catch (err) {
    uploadStatus.value = `上传失败：${err.message}`
  }
  e.target.value = ''
  setTimeout(() => { uploadStatus.value = '' }, 4000)
}
</script>
