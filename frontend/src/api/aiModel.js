import request from '@/utils/request'

/**
 * 获取扁平化模型列表（前端下拉选项用）
 * @param {string} modelType - 模型类型筛选：text / image / video
 * @param {string} modelProvider - 模型供应商筛选
 * @param {Object} [opts]
 * @param {boolean} [opts.availableOnly] - 仅返回当前用户已启用且配置了 API Key 的模型
 */
export function getModelOptions(modelType, modelProvider, opts = {}) {
  return request.get('/models/flat', {
    params: {
      model_type: modelType,
      model_provider: modelProvider,
      available_only: opts.availableOnly ? true : undefined,
    }
  })
}

/**
 * 获取按供应商分组的模型列表
 * @param {string} modelType - 模型类型筛选：text / image / video
 */
export function getModelsGrouped(modelType) {
  return request.get('/models', { params: { model_type: modelType } })
}
