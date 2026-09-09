import request from '@/utils/request'

export function getDictData(dictName) {
  return request.get('/sys_dict', { params: { dict_name: dictName } })
}
