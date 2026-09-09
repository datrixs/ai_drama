import { ref } from 'vue'
import { useDictStore } from '@/store/dict'

export function useDict(...args) {
  const dictStore = useDictStore()
  const res = {}

  args.forEach((dictName) => {
    const dictRef = ref([])
    res[dictName] = dictRef
    dictStore.loadDict(dictName).then((data) => {
      dictRef.value = data
    })
  })

  return res
}
