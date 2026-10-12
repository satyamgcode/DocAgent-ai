<template>
  <div 
    v-if="isOpen" 
    class="modal-overlay open"
    @click.self="close"
  >
    <div class="modal w-full max-w-lg bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-5 shadow-2xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-gray-100 pb-4">
        <h3 class="text-sm font-bold text-slate-900 font-heading flex items-center gap-2">
          <i class="mdi mdi-cog-outline text-darkTeal text-lg"></i> AI Model & API Key Settings
        </h3>
        <button class="text-xl text-slate-400 hover:text-slate-900 cursor-pointer" @click="close">&times;</button>
      </div>

      <!-- Provider Tabs -->
      <div class="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
        <button
          v-for="tab in providerTabs"
          :key="tab.id"
          type="button"
          @click="activeTab = tab.id"
          :class="[
            'flex-1 py-1.5 px-2 text-[10px] font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer',
            activeTab === tab.id 
              ? 'bg-white text-darkTeal shadow-sm' 
              : 'text-slate-600 hover:text-slate-900'
          ]"
        >
          <i :class="tab.icon"></i>
          <span>{{ tab.label }}</span>
          <span 
            v-if="isProviderConfigured(tab.id)"
            class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" 
            title="Key configured"
          ></span>
        </button>
      </div>

      <!-- Tab Content -->
      <div class="flex flex-col gap-4">
        <!-- 1. Google Gemini Tab -->
        <div v-if="activeTab === 'gemini'" class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <div class="flex items-center justify-between">
              <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Google Gemini API Key</label>
              <span v-if="globalKeysAvailable?.gemini" class="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                <i class="mdi mdi-check-circle"></i> Configured via .env
              </span>
            </div>
            <div class="relative flex items-center">
              <i class="mdi mdi-google absolute left-4 text-darkTeal text-base"></i>
              <input 
                v-model="geminiKey" 
                type="password" 
                placeholder="Google AI Studio Key (AIzaSy...)" 
                class="w-full bg-white border border-gray-300 focus:border-darkTeal focus:ring-1 focus:ring-darkTeal/20 outline-none rounded-xl py-2.5 pl-11 pr-4 text-xs text-slate-900 placeholder-gray-400 transition-all font-medium"
              >
            </div>
            <span class="text-[9px] text-slate-500 font-medium">
              Get your free key from <a href="https://aistudio.google.com/" target="_blank" class="text-darkTeal underline font-semibold">Google AI Studio</a> or specify <code>GEMINI_API_KEY</code> in <code>.env</code>.
            </span>
          </div>
        </div>

        <!-- 2. OpenAI Tab -->
        <div v-else-if="activeTab === 'openai'" class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <div class="flex items-center justify-between">
              <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">OpenAI API Key</label>
              <span v-if="globalKeysAvailable?.openai" class="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                <i class="mdi mdi-check-circle"></i> Configured via .env
              </span>
            </div>
            <div class="relative flex items-center">
              <i class="mdi mdi-creation absolute left-4 text-darkTeal text-base"></i>
              <input 
                v-model="openaiKey" 
                type="password" 
                placeholder="OpenAI API Key (sk-...)" 
                class="w-full bg-white border border-gray-300 focus:border-darkTeal focus:ring-1 focus:ring-darkTeal/20 outline-none rounded-xl py-2.5 pl-11 pr-4 text-xs text-slate-900 placeholder-gray-400 transition-all font-medium"
              >
            </div>
            <span class="text-[9px] text-slate-500 font-medium">
              Compatible with GPT-4o, GPT-4o-mini, GPT-3.5. Or specify <code>OPENAI_API_KEY</code> in <code>.env</code>.
            </span>
          </div>
        </div>

        <!-- 3. Anthropic Claude Tab -->
        <div v-else-if="activeTab === 'claude'" class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <div class="flex items-center justify-between">
              <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Anthropic Claude API Key</label>
              <span v-if="globalKeysAvailable?.claude" class="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                <i class="mdi mdi-check-circle"></i> Configured via .env
              </span>
            </div>
            <div class="relative flex items-center">
              <i class="mdi mdi-robot-outline absolute left-4 text-darkTeal text-base"></i>
              <input 
                v-model="claudeKey" 
                type="password" 
                placeholder="Anthropic API Key (sk-ant-...)" 
                class="w-full bg-white border border-gray-300 focus:border-darkTeal focus:ring-1 focus:ring-darkTeal/20 outline-none rounded-xl py-2.5 pl-11 pr-4 text-xs text-slate-900 placeholder-gray-400 transition-all font-medium"
              >
            </div>
            <span class="text-[9px] text-slate-500 font-medium">
              Compatible with Claude 3.5 Sonnet & Haiku. Or specify <code>ANTHROPIC_API_KEY</code> in <code>.env</code>.
            </span>
          </div>
        </div>

        <!-- 4. Generic / Custom OpenAI-Compatible Tab -->
        <div v-else-if="activeTab === 'generic'" class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <div class="flex items-center justify-between">
              <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Generic / Custom API Key</label>
              <span v-if="globalKeysAvailable?.generic || globalKeysAvailable?.groq || globalKeysAvailable?.openrouter" class="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                <i class="mdi mdi-check-circle"></i> Configured via .env
              </span>
            </div>
            <div class="relative flex items-center">
              <i class="mdi mdi-key-variant absolute left-4 text-darkTeal text-base"></i>
              <input 
                v-model="genericKey" 
                type="password" 
                placeholder="API Key (Groq, OpenRouter, DeepSeek, or leave empty for Ollama)" 
                class="w-full bg-white border border-gray-300 focus:border-darkTeal focus:ring-1 focus:ring-darkTeal/20 outline-none rounded-xl py-2.5 pl-11 pr-4 text-xs text-slate-900 placeholder-gray-400 transition-all font-medium"
              >
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Custom Base URL (OpenAI-compatible)</label>
            <div class="relative flex items-center">
              <i class="mdi mdi-web absolute left-4 text-darkTeal text-base"></i>
              <input 
                v-model="genericBaseUrl" 
                type="text" 
                placeholder="e.g. https://api.groq.com/openai/v1 or http://localhost:11434/v1" 
                class="w-full bg-white border border-gray-300 focus:border-darkTeal focus:ring-1 focus:ring-darkTeal/20 outline-none rounded-xl py-2.5 pl-11 pr-4 text-xs text-slate-900 placeholder-gray-400 transition-all font-medium"
              >
            </div>
            <span class="text-[9px] text-slate-500 font-medium">
              Examples: <code>https://api.groq.com/openai/v1</code>, <code>https://openrouter.ai/api/v1</code>, or local <code>http://localhost:11434/v1</code>.
            </span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Default Model Name</label>
            <div class="relative flex items-center">
              <i class="mdi mdi-tag-outline absolute left-4 text-darkTeal text-base"></i>
              <input 
                v-model="genericModel" 
                type="text" 
                placeholder="e.g. llama-3.3-70b-versatile or deepseek-chat" 
                class="w-full bg-white border border-gray-300 focus:border-darkTeal focus:ring-1 focus:ring-darkTeal/20 outline-none rounded-xl py-2.5 pl-11 pr-4 text-xs text-slate-900 placeholder-gray-400 transition-all font-medium"
              >
            </div>
          </div>
        </div>

        <div class="border-t border-gray-100 pt-3 flex flex-col gap-3">
          <!-- Chatbot ID -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Your Unique Chatbot ID</label>
            <div class="relative flex items-center">
              <i class="mdi mdi-identifier absolute left-4 text-darkTeal text-base"></i>
              <input 
                :value="chatbotId" 
                type="text" 
                readonly 
                class="w-full bg-slate-50 border border-gray-200 outline-none rounded-xl py-2 pl-11 pr-4 text-xs text-slate-600 cursor-not-allowed font-medium"
              >
            </div>
          </div>

          <!-- RAG Matches Slider -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">RAG Context Search Matches</label>
            <div class="flex items-center gap-3">
              <input 
                v-model.number="inputRagLimit" 
                type="range" 
                min="2" 
                max="10" 
                class="flex-grow accent-darkTeal"
              >
              <span class="text-xs font-bold text-darkTeal min-w-[50px]">{{ inputRagLimit }} Chunks</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3 border-t border-gray-100 pt-4">
        <button 
          class="px-4 py-2 text-xs font-bold rounded-full text-slate-600 border border-gray-300 hover:bg-slate-50 transition-all cursor-pointer"
          @click="close"
        >
          Cancel
        </button>
        <button 
          class="px-5 py-2 text-xs font-bold rounded-full bg-darkTeal text-white shadow-md shadow-darkTeal/10 hover:bg-darkTeal/90 transition-all cursor-pointer"
          :disabled="saving"
          @click="handleSave"
        >
          {{ saving ? 'Saving...' : 'Save Configuration' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useChat } from '../../composables/useChat'

const props = defineProps({
  isOpen: Boolean
})

const emit = defineEmits(['close'])

const { apiKey, settings, chatbotId, globalKeysAvailable, updateSettings } = useAuth()
const { ragLimit, setRagLimit } = useChat()

const activeTab = ref('gemini')
const geminiKey = ref('')
const openaiKey = ref('')
const claudeKey = ref('')
const genericKey = ref('')
const genericBaseUrl = ref('')
const genericModel = ref('')
const inputRagLimit = ref(4)
const saving = ref(false)

const providerTabs = [
  { id: 'gemini', label: 'Gemini', icon: 'mdi mdi-google' },
  { id: 'openai', label: 'OpenAI', icon: 'mdi mdi-creation' },
  { id: 'claude', label: 'Claude', icon: 'mdi mdi-robot-outline' },
  { id: 'generic', label: 'Generic / Local', icon: 'mdi mdi-server-network' }
]

function isProviderConfigured(providerId) {
  if (providerId === 'gemini') {
    return !!(geminiKey.value || globalKeysAvailable.value?.gemini)
  } else if (providerId === 'openai') {
    return !!(openaiKey.value || globalKeysAvailable.value?.openai)
  } else if (providerId === 'claude') {
    return !!(claudeKey.value || globalKeysAvailable.value?.claude)
  } else if (providerId === 'generic') {
    return !!(genericKey.value || genericBaseUrl.value || globalKeysAvailable.value?.generic || globalKeysAvailable.value?.groq || globalKeysAvailable.value?.openrouter)
  }
  return false
}

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    const s = settings.value || {}
    geminiKey.value = s.gemini_key || apiKey.value || ''
    openaiKey.value = s.openai_key || ''
    claudeKey.value = s.claude_key || ''
    genericKey.value = s.generic_key || ''
    genericBaseUrl.value = s.generic_base_url || ''
    genericModel.value = s.generic_model || ''
    inputRagLimit.value = ragLimit.value || 4
  }
})

function close() {
  emit('close')
}

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      api_key: geminiKey.value.trim() || apiKey.value,
      gemini_key: geminiKey.value.trim(),
      openai_key: openaiKey.value.trim(),
      claude_key: claudeKey.value.trim(),
      generic_key: genericKey.value.trim(),
      generic_base_url: genericBaseUrl.value.trim(),
      generic_model: genericModel.value.trim()
    }
    await updateSettings(payload)
    setRagLimit(inputRagLimit.value)
    alert("Configuration saved successfully!")
    close()
  } catch (err) {
    alert(`Error saving configuration: ${err.message}`)
  } finally {
    saving.value = false
  }
}
</script>
