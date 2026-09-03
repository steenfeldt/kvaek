<script setup lang="ts">
import { computed } from "vue";
import { splitHashtags } from "../lib/hashtags";

const props = defineProps<{ text: string }>();
const parts = computed(() => splitHashtags(props.text));
</script>

<template>
  <span class="whitespace-pre-line">
    <template v-for="(part, i) in parts" :key="i">
      <span v-if="part.tag" class="font-medium text-fjord-700">{{ part.text }}</span>
      <template v-else>{{ part.text }}</template>
    </template>
  </span>
</template>
