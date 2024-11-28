const express = require('express');
const path = require('path');
const cors = require('cors');
const app = express();
const { createProxyMiddleware } = require('http-proxy-middleware');
// CORS 설정
app.use(cors({
    origin: '*', // 개발 환경에서는 모든 origin 허용
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// JSON body parsing
app.use(express.json());

// 정적 파일 서빙
app.use(express.static(path.join(__dirname, 'static')));

// 모든 라우트를 index.html로 리다이렉트
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'static', 'index.html'));
});


app.use('/api', createProxyMiddleware({
    target: 'http://localhost:8080',
    changeOrigin: true,
    secure: false,
    pathRewrite: {
        '^/api': ''
    },
    onProxyRes: function(proxyRes, req, res) {
        proxyRes.headers['Access-Control-Allow-Origin'] = '*';
    }
}));


const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Client server is running on port ${PORT}`);
});
