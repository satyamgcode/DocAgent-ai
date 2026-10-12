<template>
  <header class="py-2.5 sm:py-3 px-3 sm:px-6 border-b border-gray-200 flex items-center justify-between bg-slate-50/50 gap-2 shrink-0">
    <div class="flex items-center gap-2 sm:gap-3 min-w-0">
      <!-- Mobile Sidebar Toggle Button -->
      <button 
        class="lg:hidden w-8.5 h-8.5 rounded-xl flex items-center justify-center bg-slate-100 border border-gray-200 text-slate-700 hover:bg-slate-200 text-base shrink-0 cursor-pointer"
        title="Open drawer"
        @click="$emit('toggleSidebar')"
      >
        <i class="mdi mdi-menu text-darkTeal"></i>
      </button>

      <div class="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-lightTeal/10 flex items-center justify-center text-darkTeal text-base sm:text-lg relative shrink-0">
        <i class="mdi mdi-robot-outline"></i>
        <span class="absolute bottom-0 right-0 w-2 sm:w-2.5 h-2 sm:h-2.5 rounded-full bg-limeGreen ring-2 ring-white"></span>
      </div>

      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="text-xs sm:text-sm font-bold text-slate-900 truncate">
            {{ isDashboardView ? 'Admin Management Dashboard' : (activeSessionTitle || 'New Chat') }}
          </h2>
          <!-- New Chat quick button in header -->
          <button 
            v-if="!isDashboardView"
            class="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-lightTeal/10 hover:bg-lightTeal/20 text-darkTeal text-[10px] font-bold transition-colors cursor-pointer"
            title="Start a new chat session"
            @click="$emit('newChat')"
          >
            <i class="mdi mdi-plus text-xs"></i>
            <span>New Chat</span>
          </button>
        </div>

        <div class="flex items-center gap-1.5 mt-0.5">
          <span 
            v-if="!isDashboardView" 
            class="text-[8px] sm:text-[9px] text-limeGreen bg-limeGreen/10 px-1.5 sm:px-2 py-0.2 rounded-full font-extrabold uppercase tracking-wider"
          >
            Session Active
          </span>
          <span 
            v-else
            class="text-[8px] sm:text-[9px] text-darkTeal bg-lightTeal/15 px-1.5 sm:px-2 py-0.2 rounded-full font-extrabold uppercase tracking-wider"
          >
            Analytics & Reviews
          </span>
        </div>
      </div>
    </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
      <!-- Admin Dashboard / Chat Toggle Button -->
      <button 
        class="py-1.5 px-2.5 sm:px-3 rounded-xl border text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
        :class="isDashboardView 
          ? 'bg-gradient-to-r from-lightTeal to-darkTeal text-white border-transparent hover:opacity-95' 
          : 'bg-white border-slate-300 text-slate-700 hover:text-darkTeal hover:border-darkTeal/40'"
        :title="isDashboardView ? 'Switch to Chat Assistant' : 'Switch to Admin Question Management Dashboard'"
        @click="$emit('toggleView')"
      >
        <i :class="isDashboardView ? 'mdi mdi-chat-outline' : 'mdi mdi-view-dashboard-outline'"></i>
        <span class="hidden sm:inline">{{ isDashboardView ? 'Back to Chat' : 'Admin Dashboard' }}</span>
      </button>

      <!-- User Profile Badge (hidden on mobile, visible from md) -->
      <div class="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-100 border border-gray-200 text-xs text-slate-700 font-bold max-w-[130px] truncate">
        <i class="mdi mdi-account-circle-outline text-sm text-darkTeal shrink-0"></i>
        <span class="truncate">{{ username }}</span>
      </div>

      <!-- Provider & Model Selector (only in chat view) -->
      <div v-if="!isDashboardView" class="relative hidden sm:flex items-center gap-2">
        <!-- Provider Select -->
        <div class="relative flex items-center">
          <i class="mdi mdi-cloud-outline absolute left-2 text-darkTeal text-xs pointer-events-none"></i>
          <select 
            v-model="selectedProvider"
            @change="handleProviderChange"
            class="bg-slate-100 border border-gray-200 rounded-xl py-1.5 pl-6 pr-5 text-[9px] sm:text-[10px] font-bold text-slate-700 outline-none focus:border-darkTeal cursor-pointer appearance-none"
            title="Choose AI Provider"
          >
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI</option>
            <option value="claude">Anthropic Claude</option>
            <option value="generic">Generic / Custom</option>
            <option value="groq">Groq</option>
            <option value="openrouter">OpenRouter</option>
          </select>
        </div>

        <!-- Model Select -->
        <div class="relative flex items-center">
          <i class="mdi mdi-brain absolute left-2 text-darkTeal text-xs pointer-events-none"></i>
          <select 
            v-model="selectedModel"
            class="bg-slate-100 border border-gray-200 rounded-xl py-1.5 pl-6 pr-5 text-[9px] sm:text-[10px] font-bold text-slate-700 outline-none focus:border-darkTeal cursor-pointer appearance-none"
            title="Choose Model"
          >
            <template v-if="selectedProvider === 'gemini'">
              <option value="models/gemini-2.0-flash">Gemini 2.0 Flash</option>
              <option value="models/gemini-1.5-flash">Gemini 1.5 Flash</option>
              <option value="models/gemini-1.5-pro">Gemini 1.5 Pro</option>
              <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
            </template>

            <template v-else-if="selectedProvider === 'openai'">
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
            </template>

            <template v-else-if="selectedProvider === 'claude'">
              <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku</option>
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
              <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
              <option value="claude-3-opus-20240229">Claude 3 Opus</option>
            </template>

            <template v-else-if="selectedProvider === 'groq'">
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
              <option value="llama-3.1-8b-instant">Llama 3.1 8B</option>
              <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
            </template>

            <template v-else-if="selectedProvider === 'openrouter'">
              <option value="meta-llama/llama-3.3-70b-instruct">Llama 3.3 70B</option>
              <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet</option>
              <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
              <option value="deepseek/deepseek-chat">DeepSeek Chat</option>
            </template>

            <template v-else>
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
              <option value="deepseek-chat">DeepSeek Chat</option>
              <option value="mistral-small-latest">Mistral Small</option>
              <option value="custom-model">Custom Model</option>
            </template>
          </select>
        </div>
      </div>

      <!-- Action Buttons -->
      <button 
        class="w-8 h-8 rounded-xl flex items-center justify-center bg-slate-100 border border-gray-200 text-slate-600 hover:text-slate-900 hover:bg-slate-200 hover:border-gray-400 transition-all text-sm cursor-pointer shrink-0"
        title="Integrate Chatbot Widget"
        @click="$emit('openWidget')"
      >
        <i class="mdi mdi-code-tags"></i>
      </button>

      <button 
        class="w-8 h-8 rounded-xl flex items-center justify-center bg-slate-100 border border-gray-200 text-slate-600 hover:text-slate-900 hover:bg-slate-200 hover:border-gray-400 transition-all text-sm cursor-pointer shrink-0"
        title="API Settings"
        @click="$emit('openSettings')"
      >
        <i class="mdi mdi-cog-outline"></i>
      </button>

      <button 
        class="w-8 h-8 rounded-xl flex items-center justify-center bg-slate-100 border border-gray-200 text-slate-600 hover:text-coralOrange hover:bg-coralOrange/10 hover:border-coralOrange/30 transition-all text-sm cursor-pointer shrink-0"
        title="Sign Out"
        @click="$emit('logout')"
      >
        <i class="mdi mdi-logout"></i>
      </button>
    </div>
  </header>
</template>

<script setup>
import { useAuth } from '../../composables/useAuth'
import { useChat } from '../../composables/useChat'

defineProps({
  isDashboardView: {
    type: Boolean,
    default: false
  }
})

defineEmits(['openWidget', 'openSettings', 'logout', 'toggleSidebar', 'toggleView', 'newChat'])

const { username } = useAuth()
const { selectedModel, selectedProvider, setProvider, activeSessionTitle } = useChat()

function handleProviderChange() {
  setProvider(selectedProvider.value)
}
</script>

