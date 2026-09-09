import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDictData } from '@/api/dict'

export const useDictStore = defineStore('dict', () => {
  const dictMap = ref({})
  const loadingMap = ref({})

  async function loadDict(dictName) {
    if (dictMap.value[dictName]) {
      return dictMap.value[dictName]
    }
    if (loadingMap.value[dictName]) {
      return loadingMap.value[dictName]
    }
    const promise = getDictData(dictName)
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        dictMap.value[dictName] = list
        delete loadingMap.value[dictName]
        return data
      })
      .catch((err) => {
        delete loadingMap.value[dictName]
        throw err
      })
    loadingMap.value[dictName] = promise
    return promise
  }

  function getDict(dictName) {
    return dictMap.value[dictName] || []
  }

  function removeDict(dictName) {
    delete dictMap.value[dictName]
  }

  function clearDict() {
    dictMap.value = {}
  }

  return { dictMap, loadDict, getDict, removeDict, clearDict }
})
