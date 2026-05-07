import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue')
    },
    {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        children: [
            {
                path: '',
                name: 'Dashboard',
                component: () => import('@/views/Dashboard.vue')
            },
            {
                path: 'prediction',
                name: 'Prediction',
                component: () => import('@/views/Prediction.vue')
            },
            {
                path: 'comparison',
                name: 'Comparison',
                component: () => import('@/views/Comparison.vue')
            },
            {
                path: 'report',
                name: 'Report',
                component: () => import('@/views/Report.vue')
            },
            {
                path: 'alarm',
                name: 'Alarm',
                component: () => import('@/views/Alarm.vue')
            },
            {
                path: 'history',
                name: 'History',
                component: () => import('@/views/History.vue')
            },
            {
                path: 'settings',
                name: 'Settings',
                component: () => import('@/views/Settings.vue')
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('solar_token')
    if (!token && to.path !== '/login') {
        next('/login')
    } else if (token && to.path === '/login') {
        next('/')
    } else {
        next()
    }
})

export default router
