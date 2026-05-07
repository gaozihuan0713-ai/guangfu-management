/**
 * 光伏发电管理平台 - 前端主逻辑
 */
(function() {
    var loadingEl = document.getElementById('app-loading');
    function hideLoading() {
        if (loadingEl) loadingEl.style.display = 'none';
    }
    function showLoadError(msg) {
        if (loadingEl) {
            loadingEl.innerHTML = '<div class="error-msg">' + (msg || '资源加载失败，请检查网络连接后刷新页面') + '</div>';
        }
    }

    if (typeof Vue === 'undefined') {
        showLoadError('Vue 框架加载失败，请检查网络连接后刷新页面');
        return;
    }
    if (typeof ElementPlus === 'undefined') {
        showLoadError('Element Plus 组件库加载失败，请检查网络连接后刷新页面');
        return;
    }
    if (typeof echarts === 'undefined') {
        showLoadError('ECharts 图表库加载失败，请检查网络连接后刷新页面');
        return;
    }

const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;

const API = {
    BASE: '',
    token: localStorage.getItem('solar_token') || '',

    async request(url, options = {}) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = 'Bearer ' + this.token;
        }
        const res = await fetch(this.BASE + url, {
            ...options,
            headers: { ...headers, ...options.headers }
        });
        if (url.includes('/export')) {
            if (res.ok) return res;
            throw new Error('导出失败');
        }
        const data = await res.json();
        if (data.code === 401) {
            this.token = '';
            localStorage.removeItem('solar_token');
            localStorage.removeItem('solar_user');
            window.location.reload();
        }
        return data;
    },

    login: (username, password) => API.request('/api/auth/login', {
        method: 'POST', body: JSON.stringify({ username, password })
    }),
    getUserInfo: () => API.request('/api/auth/info'),
    changePassword: (old_password, new_password) => API.request('/api/auth/change-password', {
        method: 'POST', body: JSON.stringify({ old_password, new_password })
    }),
    getUsers: () => API.request('/api/auth/users'),
    createUser: (data) => API.request('/api/auth/users', {
        method: 'POST', body: JSON.stringify(data)
    }),
    updateUser: (id, data) => API.request('/api/auth/users/' + id, {
        method: 'PUT', body: JSON.stringify(data)
    }),
    deleteUser: (id) => API.request('/api/auth/users/' + id, { method: 'DELETE' }),

    getRealtime: (hours) => API.request('/api/data/realtime?hours=' + (hours || 24)),
    getPredict: (hours) => API.request('/api/data/predict?hours=' + (hours || 6)),
    getComparison: (hours) => API.request('/api/data/comparison?hours=' + (hours || 6)),
    getDashboard: () => API.request('/api/data/dashboard'),
    getHistory: (page, per_page, start_date, end_date) => {
        let url = '/api/data/history?page=' + (page || 1) + '&per_page=' + (per_page || 50);
        if (start_date) url += '&start_date=' + start_date;
        if (end_date) url += '&end_date=' + end_date;
        return API.request(url);
    },
    exportData: (type, start_date, end_date) => {
        let url = '/api/data/export?type=' + (type || 'history');
        if (start_date) url += '&start_date=' + start_date;
        if (end_date) url += '&end_date=' + end_date;
        return API.request(url);
    },

    getAlarms: (page, per_page, filters) => {
        let url = '/api/alarm/list?page=' + (page || 1) + '&per_page=' + (per_page || 20);
        if (filters && filters.status) url += '&status=' + filters.status;
        if (filters && filters.level) url += '&level=' + filters.level;
        if (filters && filters.alarm_type) url += '&alarm_type=' + filters.alarm_type;
        return API.request(url);
    },
    getAlarmStats: () => API.request('/api/alarm/stats'),
    checkAlarms: () => API.request('/api/alarm/check', { method: 'POST' }),
    ackAlarm: (id) => API.request('/api/alarm/' + id + '/ack', { method: 'POST' }),
    batchAckAlarms: (ids) => API.request('/api/alarm/batch-ack', {
        method: 'POST', body: JSON.stringify({ ids })
    }),
    resolveAlarm: (id) => API.request('/api/alarm/' + id + '/resolve', { method: 'POST' })
};

const app = createApp({
    setup() {
        const isLoggedIn = ref(!!API.token);
        const currentUser = reactive(JSON.parse(localStorage.getItem('solar_user') || '{}'));
        const loginForm = reactive({ username: '', password: '' });
        const loginLoading = ref(false);
        const loginFormRef = ref(null);
        const loginRules = {
            username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
            password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
        };

        const isCollapse = ref(false);
        const currentView = ref('dashboard');
        const menuLabels = {
            dashboard: '系统首页', prediction: '发电预测', comparison: '功率对比',
            report: '报表导出', alarm: '故障报警', history: '历史数据', settings: '系统设置'
        };

        const dashboardData = reactive({});
        const realtimeHours = ref(24);
        const alarmStats = reactive({ by_level: {}, by_status: {}, unacked: 0, today_count: 0 });

        const predHours = ref(6);
        const predictionData = ref([]);
        const predLoading = ref(false);

        const compHours = ref(6);
        const compLoading = ref(false);
        const compStats = reactive({ mae: '-', rmse: '-', mape: '-', accuracy: '-' });

        const exportForm = reactive({ start_date: '', end_date: '', type: 'history' });
        const exportLoading = ref(false);
        const previewLoading = ref(false);
        const previewData = ref([]);
        const previewTotal = ref(0);

        const alarmList = ref([]);
        const alarmTotal = ref(0);
        const alarmPage = ref(1);
        const alarmPerPage = 20;
        const alarmFilter = reactive({ status: '', level: '', alarm_type: '' });
        const selectedAlarms = ref([]);
        const checkLoading = ref(false);

        const historyList = ref([]);
        const historyTotal = ref(0);
        const historyPage = ref(1);
        const historyFilter = reactive({ start_date: '', end_date: '' });

        const userList = ref([]);
        const userDialogVisible = ref(false);
        const userDialogTitle = ref('新增用户');
        const userForm = reactive({ id: null, username: '', password: '', real_name: '', role: 'operator', status: 1 });
        const passwordDialogVisible = ref(false);
        const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' });

        const charts = {};

        async function handleLogin() {
            loginLoading.value = true;
            try {
                const res = await API.login(loginForm.username, loginForm.password);
                if (res.code === 200) {
                    API.token = res.data.token;
                    localStorage.setItem('solar_token', res.data.token);
                    localStorage.setItem('solar_user', JSON.stringify(res.data.user));
                    Object.assign(currentUser, res.data.user);
                    isLoggedIn.value = true;
                    ElementPlus.ElMessage.success('登录成功');
                    await nextTick();
                    loadDashboard();
                    loadAlarmStats();
                } else {
                    ElementPlus.ElMessage.error(res.message || '登录失败');
                }
            } catch (e) {
                ElementPlus.ElMessage.error('网络错误');
            }
            loginLoading.value = false;
        }

        function handleLogout() {
            API.token = '';
            localStorage.removeItem('solar_token');
            localStorage.removeItem('solar_user');
            isLoggedIn.value = false;
        }

        function handleUserCommand(cmd) {
            if (cmd === 'logout') handleLogout();
            else if (cmd === 'password') passwordDialogVisible.value = true;
            else if (cmd === 'profile') ElementPlus.ElMessage.info('当前用户: ' + currentUser.username);
        }

        async function loadDashboard() {
            const res = await API.getDashboard();
            if (res.code === 200) {
                Object.assign(dashboardData, res.data);
            }
            await loadRealtimeData();
            await loadPredictionData();
            await loadEnvData();
        }

        async function loadRealtimeData() {
            const res = await API.getRealtime(realtimeHours.value);
            if (res.code === 200) {
                renderRealtimeChart(res.data);
            }
        }

        async function loadPredictionData() {
            predLoading.value = true;
            try {
                const res = await API.getPredict(predHours.value);
                if (res.code === 200) {
                    predictionData.value = res.data;
                    if (currentView.value === 'prediction') {
                        renderPredictionChart(res.data);
                    } else {
                        renderPredictMiniChart(res.data);
                    }
                }
            } catch (e) {
                console.error('加载预测数据失败', e);
            }
            predLoading.value = false;
        }

        async function loadEnvData() {
            const res = await API.getRealtime(6);
            if (res.code === 200 && res.data.length > 0) {
                renderEnvChart(res.data);
            }
        }

        async function loadComparisonData() {
            compLoading.value = true;
            try {
                const res = await API.getComparison(compHours.value);
                if (res.code === 200) {
                    renderComparisonChart(res.data.actual, res.data.predicted);
                    calculateCompStats(res.data.actual, res.data.predicted);
                }
            } catch (e) {
                console.error('加载对比数据失败', e);
            }
            compLoading.value = false;
        }

        function calculateCompStats(actual, predicted) {
            if (!actual || actual.length === 0) return;
            let sumAbsErr = 0, sumSqErr = 0, sumAbsPercErr = 0, count = 0;
            for (let i = 0; i < actual.length; i++) {
                const a = actual[i].active_power;
                const p = predicted[i] ? predicted[i].predicted_power : a;
                const diff = a - p;
                sumAbsErr += Math.abs(diff);
                sumSqErr += diff * diff;
                if (p > 0) {
                    sumAbsPercErr += Math.abs(diff / p);
                    count++;
                }
            }
            const n = actual.length;
            compStats.mae = (sumAbsErr / n).toFixed(2);
            compStats.rmse = Math.sqrt(sumSqErr / n).toFixed(2);
            compStats.mape = count > 0 ? (sumAbsPercErr / count * 100).toFixed(1) : '-';
            compStats.accuracy = count > 0 ? (100 - sumAbsPercErr / count * 100).toFixed(1) : '-';
        }

        async function handleExport() {
            exportLoading.value = true;
            try {
                const res = await API.exportData(exportForm.type, exportForm.start_date, exportForm.end_date);
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'solar_' + exportForm.type + '_' + (exportForm.start_date || 'all') + '_' + (exportForm.end_date || 'all') + '.csv';
                a.click();
                window.URL.revokeObjectURL(url);
                ElementPlus.ElMessage.success('导出成功');
            } catch (e) {
                ElementPlus.ElMessage.error('导出失败');
            }
            exportLoading.value = false;
        }

        async function previewReport() {
            previewLoading.value = true;
            const res = await API.getHistory(1, 50, exportForm.start_date, exportForm.end_date);
            previewLoading.value = false;
            if (res.code === 200) {
                previewData.value = res.data.records;
                previewTotal.value = res.data.total;
            }
        }

        async function loadAlarms() {
            const res = await API.getAlarms(alarmPage.value, alarmPerPage, alarmFilter);
            if (res.code === 200) {
                alarmList.value = res.data.records;
                alarmTotal.value = res.data.total;
            }
        }

        async function loadAlarmStats() {
            const res = await API.getAlarmStats();
            if (res.code === 200) {
                Object.assign(alarmStats, res.data);
            }
        }

        async function runAlarmCheck() {
            checkLoading.value = true;
            try {
                const res = await API.checkAlarms();
                if (res.code === 200) {
                    ElementPlus.ElMessage.success(res.message);
                    loadAlarms();
                    loadAlarmStats();
                }
            } catch (e) {
                ElementPlus.ElMessage.error('报警检测失败');
            }
            checkLoading.value = false;
        }

        async function ackAlarm(id) {
            const res = await API.ackAlarm(id);
            if (res.code === 200) {
                ElementPlus.ElMessage.success('已确认');
                loadAlarms();
                loadAlarmStats();
            }
        }

        async function resolveAlarm(id) {
            const res = await API.resolveAlarm(id);
            if (res.code === 200) {
                ElementPlus.ElMessage.success('已解除');
                loadAlarms();
                loadAlarmStats();
            }
        }

        function handleAlarmSelection(selection) {
            selectedAlarms.value = selection.filter(function(s) { return s.status === 'unacked'; }).map(function(s) { return s.id; });
        }

        async function batchAckAlarms() {
            if (selectedAlarms.value.length === 0) return;
            const res = await API.batchAckAlarms(selectedAlarms.value);
            if (res.code === 200) {
                ElementPlus.ElMessage.success(res.message);
                loadAlarms();
                loadAlarmStats();
            }
        }

        function resetAlarmFilter() {
            alarmFilter.status = '';
            alarmFilter.level = '';
            alarmFilter.alarm_type = '';
            alarmPage.value = 1;
            loadAlarms();
        }

        async function loadHistory() {
            const res = await API.getHistory(historyPage.value, 50, historyFilter.start_date, historyFilter.end_date);
            if (res.code === 200) {
                historyList.value = res.data.records;
                historyTotal.value = res.data.total;
            }
        }

        function resetHistoryFilter() {
            historyFilter.start_date = '';
            historyFilter.end_date = '';
            historyPage.value = 1;
            loadHistory();
        }

        async function loadUsers() {
            const res = await API.getUsers();
            if (res.code === 200) userList.value = res.data;
        }

        function showAddUserDialog() {
            userDialogTitle.value = '新增用户';
            Object.assign(userForm, { id: null, username: '', password: '', real_name: '', role: 'operator', status: 1 });
            userDialogVisible.value = true;
        }

        function showEditUserDialog(user) {
            userDialogTitle.value = '编辑用户';
            Object.assign(userForm, { ...user, password: '' });
            userDialogVisible.value = true;
        }

        async function saveUser() {
            if (!userForm.username) { ElementPlus.ElMessage.warning('请输入用户名'); return; }
            if (!userForm.id && !userForm.password) { ElementPlus.ElMessage.warning('请输入密码'); return; }
            let res;
            if (userForm.id) {
                const data = { ...userForm };
                if (!data.password) delete data.password;
                res = await API.updateUser(userForm.id, data);
            } else {
                res = await API.createUser(userForm);
            }
            if (res.code === 200) {
                ElementPlus.ElMessage.success(res.message);
                userDialogVisible.value = false;
                loadUsers();
            } else {
                ElementPlus.ElMessage.error(res.message);
            }
        }

        async function deleteUser(user) {
            try {
                await ElementPlus.ElMessageBox.confirm('确定删除用户 "' + user.username + '" ?', '确认删除', { type: 'warning' });
                const res = await API.deleteUser(user.id);
                if (res.code === 200) {
                    ElementPlus.ElMessage.success('已删除');
                    loadUsers();
                }
            } catch (e) { /* cancel */ }
        }

        async function changePassword() {
            if (passwordForm.new_password !== passwordForm.confirm_password) {
                ElementPlus.ElMessage.warning('两次密码不一致');
                return;
            }
            if (passwordForm.new_password.length < 6) {
                ElementPlus.ElMessage.warning('密码长度不能少于6位');
                return;
            }
            const res = await API.changePassword(passwordForm.old_password, passwordForm.new_password);
            if (res.code === 200) {
                ElementPlus.ElMessage.success('密码修改成功');
                passwordDialogVisible.value = false;
                Object.assign(passwordForm, { old_password: '', new_password: '', confirm_password: '' });
            } else {
                ElementPlus.ElMessage.error(res.message);
            }
        }

        function handleMenuSelect(index) {
            currentView.value = index;
            nextTick(function() {
                if (index === 'dashboard') loadDashboard();
                else if (index === 'prediction') loadPredictionData();
                else if (index === 'comparison') loadComparisonData();
                else if (index === 'alarm') { loadAlarms(); loadAlarmStats(); }
                else if (index === 'history') loadHistory();
                else if (index === 'settings') loadUsers();
            });
        }

        function getPowerLevel(power) {
            if (power > 80) return { label: '高功率', type: 'danger' };
            if (power > 30) return { label: '中功率', type: 'warning' };
            if (power > 5) return { label: '低功率', type: 'info' };
            return { label: '微功率', type: 'success' };
        }

        function initChart(el) {
            if (!el) return null;
            var rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return null;
            return echarts.init(el);
        }

        function renderRealtimeChart(data) {
            nextTick(function() {
                var el = document.querySelector('.page-dashboard .chart-container');
                if (!el) return;
                if (charts.realtime) charts.realtime.dispose();
                var chart = initChart(el);
                if (!chart) return;
                charts.realtime = chart;

                var times = data.map(function(d) { return d.timestamp.substring(11, 16); });
                var powers = data.map(function(d) { return d.active_power; });
                var radiations = data.map(function(d) { return d.radiation; });

                chart.setOption({
                    tooltip: { trigger: 'axis' },
                    legend: { data: ['发电功率', '辐照度'] },
                    grid: { left: 60, right: 60, bottom: 40, top: 40 },
                    xAxis: { type: 'category', data: times, axisLabel: { interval: Math.floor(times.length / 8) } },
                    yAxis: [
                        { type: 'value', name: '功率(kW)', position: 'left' },
                        { type: 'value', name: '辐照(W/m²)', position: 'right' }
                    ],
                    series: [
                        {
                            name: '发电功率', type: 'line', data: powers, smooth: true,
                            itemStyle: { color: '#409eff' }, areaStyle: { color: 'rgba(64,158,255,0.15)' }
                        },
                        {
                            name: '辐照度', type: 'line', data: radiations, smooth: true, yAxisIndex: 1,
                            itemStyle: { color: '#e6a23c' }, lineStyle: { type: 'dashed' }
                        }
                    ]
                });
                window.addEventListener('resize', function() { chart.resize(); });
            });
        }

        function renderPredictMiniChart(data) {
            nextTick(function() {
                var els = document.querySelectorAll('.page-dashboard .chart-container');
                var el = els[1];
                if (!el) return;
                if (charts.predictMini) charts.predictMini.dispose();
                var chart = initChart(el);
                if (!chart) return;
                charts.predictMini = chart;

                var times = data.map(function(d) { return d.timestamp.substring(11, 16); });
                var powers = data.map(function(d) { return d.predicted_power; });

                chart.setOption({
                    tooltip: { trigger: 'axis' },
                    grid: { left: 50, right: 20, bottom: 30, top: 20 },
                    xAxis: { type: 'category', data: times },
                    yAxis: { type: 'value', name: 'kW' },
                    series: [{
                        type: 'line', data: powers, smooth: true,
                        itemStyle: { color: '#67c23a' },
                        areaStyle: { color: 'rgba(103,194,58,0.2)' }
                    }]
                });
                window.addEventListener('resize', function() { chart.resize(); });
            });
        }

        function renderPredictionChart(data) {
            nextTick(function() {
                var el = document.querySelector('.page-prediction .chart-container-lg');
                if (!el) return;
                if (charts.prediction) charts.prediction.dispose();
                var chart = initChart(el);
                if (!chart) return;
                charts.prediction = chart;

                var times = data.map(function(d) { return d.timestamp.substring(5, 16); });
                var powers = data.map(function(d) { return d.predicted_power; });

                chart.setOption({
                    tooltip: { trigger: 'axis', formatter: function(params) {
                        var p = params[0];
                        return p.axisValue + '<br/>预测功率: <b>' + p.value + ' kW</b>';
                    }},
                    grid: { left: 60, right: 30, bottom: 40, top: 40 },
                    xAxis: { type: 'category', data: times, axisLabel: { rotate: 30 } },
                    yAxis: { type: 'value', name: '功率 (kW)' },
                    series: [{
                        type: 'line', data: powers, smooth: true,
                        itemStyle: { color: '#409eff' },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(64,158,255,0.3)' },
                                { offset: 1, color: 'rgba(64,158,255,0.02)' }
                            ])
                        },
                        markPoint: { data: [{ type: 'max', name: '最大值' }, { type: 'min', name: '最小值' }] },
                        markLine: { data: [{ type: 'average', name: '平均值' }] }
                    }]
                });
                window.addEventListener('resize', function() { chart.resize(); });
            });
        }

        function renderComparisonChart(actual, predicted) {
            nextTick(function() {
                var el = document.querySelector('.page-comparison .chart-container-lg');
                if (!el) return;
                if (charts.comparison) charts.comparison.dispose();
                var chart = initChart(el);
                if (!chart) return;
                charts.comparison = chart;

                var times = actual.map(function(d) { return d.timestamp.substring(11, 16); });
                var actualPowers = actual.map(function(d) { return d.active_power; });
                var predPowers = predicted.map(function(d) { return d.predicted_power; });

                chart.setOption({
                    tooltip: { trigger: 'axis' },
                    legend: { data: ['实际功率', '预测功率'] },
                    grid: { left: 60, right: 30, bottom: 40, top: 50 },
                    xAxis: { type: 'category', data: times, axisLabel: { interval: Math.floor(times.length / 10) } },
                    yAxis: { type: 'value', name: '功率 (kW)' },
                    series: [
                        {
                            name: '实际功率', type: 'line', data: actualPowers, smooth: true,
                            itemStyle: { color: '#409eff' }, lineStyle: { width: 2 }
                        },
                        {
                            name: '预测功率', type: 'line', data: predPowers, smooth: true,
                            itemStyle: { color: '#67c23a' }, lineStyle: { width: 2, type: 'dashed' }
                        }
                    ]
                });
                window.addEventListener('resize', function() { chart.resize(); });

                var devEl = document.querySelector('.page-comparison .chart-container-sm');
                if (devEl) {
                    if (charts.deviation) charts.deviation.dispose();
                    var devChart = initChart(devEl);
                    if (devChart) {
                        charts.deviation = devChart;
                        var deviations = actual.map(function(d, i) {
                            var pred = predicted[i] ? predicted[i].predicted_power : d.active_power;
                            return Math.round((d.active_power - pred) * 100) / 100;
                        });
                        devChart.setOption({
                            tooltip: { trigger: 'axis' },
                            grid: { left: 60, right: 20, bottom: 30, top: 30 },
                            xAxis: { type: 'category', data: times },
                            yAxis: { type: 'value', name: '偏差(kW)' },
                            series: [{
                                type: 'bar', data: deviations,
                                itemStyle: {
                                    color: function(params) { return params.value >= 0 ? '#67c23a' : '#f56c6c'; }
                                }
                            }]
                        });
                        window.addEventListener('resize', function() { devChart.resize(); });
                    }
                }
            });
        }

        function renderEnvChart(data) {
            nextTick(function() {
                var els = document.querySelectorAll('.page-dashboard .chart-container');
                var el = els[2];
                if (!el) return;
                if (charts.env) charts.env.dispose();
                var chart = initChart(el);
                if (!chart) return;
                charts.env = chart;

                var times = data.map(function(d) { return d.timestamp.substring(11, 16); });

                chart.setOption({
                    tooltip: { trigger: 'axis' },
                    legend: { data: ['温度', '湿度', '风速'] },
                    grid: { left: 50, right: 50, bottom: 30, top: 40 },
                    xAxis: { type: 'category', data: times },
                    yAxis: [
                        { type: 'value', name: '°C / %' },
                        { type: 'value', name: 'm/s', position: 'right' }
                    ],
                    series: [
                        { name: '温度', type: 'line', data: data.map(function(d) { return d.temperature; }), smooth: true, itemStyle: { color: '#f56c6c' } },
                        { name: '湿度', type: 'line', data: data.map(function(d) { return d.humidity; }), smooth: true, itemStyle: { color: '#409eff' } },
                        { name: '风速', type: 'bar', data: data.map(function(d) { return d.wind_speed; }), yAxisIndex: 1, itemStyle: { color: '#67c23a' } }
                    ]
                });
                window.addEventListener('resize', function() { chart.resize(); });
            });
        }

        onMounted(function() {
            if (isLoggedIn.value) {
                loadDashboard();
                loadAlarmStats();
            }
        });

        return {
            isLoggedIn, currentUser, loginForm, loginLoading, loginFormRef, loginRules,
            isCollapse, currentView, menuLabels,
            dashboardData, realtimeHours, alarmStats,
            predHours, predictionData, predLoading,
            compHours, compLoading, compStats,
            exportForm, exportLoading, previewLoading, previewData, previewTotal,
            alarmList, alarmTotal, alarmPage, alarmPerPage, alarmFilter, selectedAlarms, checkLoading,
            historyList, historyTotal, historyPage, historyFilter,
            userList, userDialogVisible, userDialogTitle, userForm,
            passwordDialogVisible, passwordForm,
            handleLogin, handleLogout, handleUserCommand, handleMenuSelect,
            loadDashboard, loadRealtimeData, loadPredictionData, loadComparisonData,
            loadAlarms, loadAlarmStats, runAlarmCheck, ackAlarm, resolveAlarm,
            batchAckAlarms, handleAlarmSelection, resetAlarmFilter,
            handleExport, previewReport,
            loadHistory, resetHistoryFilter,
            showAddUserDialog, showEditUserDialog, saveUser, deleteUser, changePassword,
            getPowerLevel
        };
    }
});

try {
    if (typeof ElementPlusIconsVue !== 'undefined') {
        for (var [key, component] of Object.entries(ElementPlusIconsVue)) {
            app.component(key, component);
        }
    }
    app.use(ElementPlus);
    app.mount('#app');
    hideLoading();
} catch (e) {
    console.error('Vue 应用挂载失败:', e);
    var errorMsg = '应用启动失败：' + e.message;
    if (e.message && e.message.includes('compiler-30')) {
        errorMsg = '模板编译错误：请检查 HTML 模板中的语法';
    }
    showLoadError(errorMsg + '<br><small>详细信息请查看浏览器控制台（F12）</small>');
}

})();
