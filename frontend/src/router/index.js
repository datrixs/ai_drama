import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/views/Auth/Login.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home/HomeView.vue'),
    meta: { title: '视频制作' }
  },
  {
    path: '/workspace',
    name: 'WorkspaceList',
    component: () => import('@/views/Workspace/WorkspaceList.vue'),
    meta: { title: '工作区', permission: 'project:read' }
  },
  {
    path: '/workspace/:projectId',
    name: 'Workspace',
    component: () => import('@/views/Workspace/Workspace.vue'),
    meta: { title: '工作区', permission: 'project:read' },
    props: true
  },
  {
    path: '/workspace/:projectId/episodes',
    name: 'EpisodePage',
    component: () => import('@/views/Episode/EpisodePage.vue'),
    meta: { title: '剧集' },
    props: true
  },
  {
    path: '/workspace/:projectId/episodes/:episodeId/storyboard',
    name: 'StoryboardEditor',
    component: () => import('@/views/Storyboard/StoryboardEditor.vue'),
    meta: { title: '分镜编辑' },
    props: true
  },
  {
    path: '/workspace/:projectId/conversation',
    name: 'Conversation',
    component: () => import('@/views/Conversation/ConversationView.vue'),
    meta: { title: 'AI对话' },
    props: true
  },
  {
    path: '/assets-center',
    name: 'AssetsCenter',
    component: () => import('@/views/AssetsCenter/AssetsCenter.vue'),
    meta: { title: '资产中心', permission: 'asset:read' }
  },
  {
    path: '/canvas',
    name: 'CanvasList',
    component: () => import('@/views/Canvas/CanvasListView.vue'),
    meta: { title: '无限画布' }
  },
  {
    path: '/canvas/:documentId',
    name: 'CanvasEditor',
    component: () => import('@/views/Canvas/CanvasEditorView.vue'),
    meta: { title: '无限画布' },
    props: true
  },
  {
    path: '/config-center',
    name: 'ConfigCenter',
    component: () => import('@/views/ConfigCenter/ConfigCenter.vue'),
    meta: { title: '设置中心' }
  },
  {
    path: '/auth/signin',
    name: 'SignIn',
    component: () => import('@/views/Auth/SignIn.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/auth/signup',
    name: 'SignUp',
    component: () => import('@/views/Auth/SignUp.vue'),
    meta: { title: '注册' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 白名单：不需要登录即可访问的路由
const WHITE_LIST = ['/', '/auth/signin', '/auth/signup']

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 皮皮虾短剧` : '皮皮虾短剧'

  const token = localStorage.getItem('token')

  // 未登录处理
  if (!token && !WHITE_LIST.includes(to.path)) {
    return next({ path: '/auth/signin', query: { redirect: to.fullPath } })
  }

  // 已登录用户访问登录页，重定向到首页
  if (token && (to.path === '/auth/signin' || to.path === '/auth/signup')) {
    return next({ path: '/home' })
  }

  next()
})

// 捕获所有未匹配的路由，重定向到首页
router.addRoute({
  path: '/:pathMatch(.*)*',
  redirect: (to) => {
    const token = localStorage.getItem('token')
    // 如果未登录，跳转到登录页
    if (!token) {
      return { path: '/auth/signin' }
    }
    // 已登录，跳转到首页
    return { path: '/home' }
  }
})

export default router
