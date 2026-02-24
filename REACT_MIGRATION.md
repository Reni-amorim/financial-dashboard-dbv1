# 🚀 Guia de Migração: Streamlit → React

Este guia explica como migrar o frontend de Streamlit para React, mantendo toda a funcionalidade.

## 📋 Por que React?

### Vantagens sobre Streamlit

| Aspecto | Streamlit | React |
|---------|-----------|-------|
| **Customização** | Limitada | Total controle |
| **Performance** | Recarrega tudo | Renderização otimizada |
| **Mobile** | OK | Excelente |
| **Design** | Componentes pré-feitos | Flexibilidade total |
| **Estado** | Session state | Redux/Context/Zustand |
| **SEO** | Ruim | Bom (com Next.js) |
| **Escalabilidade** | Média | Alta |

### Quando Migrar?

✅ **Migre para React quando:**
- Precisar de UX altamente customizada
- Mobile-first for prioridade
- Precisar de performance extrema
- Quiser controle total do UI/UX
- Planejar SaaS profissional

⏸️ **Mantenha Streamlit quando:**
- Protótipo/MVP rápido
- Dashboard interno da empresa
- Foco em análise de dados
- Time pequeno sem front-end specialist

---

## 🏗️ Arquitetura React

```
frontend-react/
├── src/
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── Dashboard/
│   │   │   ├── MetricsCard.tsx
│   │   │   ├── RevenueChart.tsx
│   │   │   └── PeriodMetrics.tsx
│   │   ├── Upload/
│   │   │   ├── FileUploader.tsx
│   │   │   └── UploadProgress.tsx
│   │   └── Layout/
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── Footer.tsx
│   │
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── UploadPage.tsx
│   │   └── HistoryPage.tsx
│   │
│   ├── services/
│   │   └── api.ts              # Axios client para FastAPI
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useUpload.ts
│   │   └── useDashboard.ts
│   │
│   ├── store/
│   │   ├── authSlice.ts        # Redux Toolkit
│   │   └── uploadSlice.ts
│   │
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces
│   │
│   ├── App.tsx
│   └── main.tsx
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## 📦 Stack Recomendada

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.14.0",
    "axios": "^1.6.2",
    "recharts": "^2.10.3",
    "@headlessui/react": "^1.7.17",
    "@heroicons/react": "^2.1.1",
    "tailwindcss": "^3.3.6",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.3",
    "vite": "^5.0.7"
  }
}
```

---

## 🔄 Equivalência de Componentes

### 1. Login (Streamlit → React)

**Streamlit:**
```python
with st.form("login_form"):
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    submit = st.form_submit_button("Entrar")
```

**React:**
```tsx
import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Usuário"
        className="w-full px-4 py-2 border rounded-lg"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Senha"
        className="w-full px-4 py-2 border rounded-lg"
      />
      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-blue-600 text-white py-2 rounded-lg"
      >
        {isLoading ? 'Entrando...' : 'Entrar'}
      </button>
    </form>
  );
}
```

### 2. Métricas do Dashboard

**Streamlit:**
```python
st.metric("Faturamento Total", f"R$ {revenue:,.2f}")
```

**React:**
```tsx
interface MetricCardProps {
  title: string;
  value: number;
  format?: 'currency' | 'number';
  delta?: number;
}

export function MetricCard({ title, value, format = 'number', delta }: MetricCardProps) {
  const formatted = format === 'currency'
    ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
    : value.toLocaleString('pt-BR');

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-gray-500 text-sm font-medium">{title}</h3>
      <p className="text-3xl font-bold mt-2">{formatted}</p>
      {delta && (
        <p className={`text-sm mt-2 ${delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
          {delta > 0 ? '↑' : '↓'} {Math.abs(delta)}%
        </p>
      )}
    </div>
  );
}
```

### 3. Upload de Arquivo

**Streamlit:**
```python
uploaded_file = st.file_uploader("Escolha um arquivo XLSX")
if uploaded_file:
    api.upload_file(uploaded_file)
```

**React:**
```tsx
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export function FileUploader() {
  const { uploadFile, isUploading, progress } = useUpload();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      await uploadFile(file);
    }
  }, [uploadFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
        ${isDragActive ? 'border-blue-600 bg-blue-50' : 'border-gray-300'}`}
    >
      <input {...getInputProps()} />
      {isUploading ? (
        <div>
          <p>Enviando... {progress}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      ) : (
        <p className="text-gray-600">
          Arraste um arquivo XLSX aqui ou clique para selecionar
        </p>
      )}
    </div>
  );
}
```

---

## 🔧 Serviço de API (TypeScript)

**`src/services/api.ts`**

```typescript
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class APIClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor para adicionar token automaticamente
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Interceptor para tratar erros
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Redireciona para login
          this.token = null;
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  async login(username: string, password: string) {
    const response = await this.client.post('/auth/login', { username, password });
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(email: string, username: string, password: string) {
    const response = await this.client.post('/auth/register', { email, username, password });
    return response.data;
  }

  async uploadFile(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post('/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress?.(progress);
        }
      },
    });

    return response.data;
  }

  async getDashboardData() {
    const response = await this.client.get('/dashboard/');
    return response.data;
  }

  async listUploads() {
    const response = await this.client.get('/upload/');
    return response.data;
  }

  async deleteUpload(id: number) {
    await this.client.delete(`/upload/${id}`);
  }
}

export const apiClient = new APIClient();
```

---

## 🎣 Custom Hooks

**`src/hooks/useAuth.ts`**

```typescript
import { create } from 'zustand';
import { apiClient } from '@/services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),

  login: async (username, password) => {
    const data = await apiClient.login(username, password);
    set({ token: data.access_token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('token');
    apiClient.setToken('');
    set({ user: null, token: null, isAuthenticated: false });
  },
}));
```

**`src/hooks/useDashboard.ts`**

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiClient.getDashboardData(),
    refetchInterval: 30000, // Atualiza a cada 30s
  });
}
```

---

## 📊 Gráficos com Recharts

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

export function RevenueChart({ data }: { data: PeriodMetrics[] }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Receita Mensal</h3>
      <LineChart width={600} height={300} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="period" />
        <YAxis />
        <Tooltip formatter={(value) => `R$ ${value.toLocaleString('pt-BR')}`} />
        <Legend />
        <Line type="monotone" dataKey="revenue" stroke="#1f77b4" name="Receita" />
        <Line type="monotone" dataKey="debits" stroke="#ff7f0e" name="Débitos" />
        <Line type="monotone" dataKey="net" stroke="#2ca02c" name="Líquido" />
      </LineChart>
    </div>
  );
}
```

---

## 🚀 Deploy

### Vite Build

```bash
npm run build
# Gera pasta dist/ com arquivos estáticos
```

### Dockerfile

```dockerfile
FROM node:20-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Vercel / Netlify

```bash
# Vercel
vercel --prod

# Netlify
netlify deploy --prod --dir=dist
```

---

## ⚡ Performance

### Code Splitting

```tsx
import { lazy, Suspense } from 'react';

const DashboardPage = lazy(() => import('@/pages/DashboardPage'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <DashboardPage />
    </Suspense>
  );
}
```

### React Query Cache

```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutos
      cacheTime: 10 * 60 * 1000, // 10 minutos
    },
  },
});
```

---

## 📱 Mobile-First

```tsx
// Responsive com Tailwind
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {metrics.map((metric) => (
    <MetricCard key={metric.title} {...metric} />
  ))}
</div>
```

---

## ✅ Checklist de Migração

- [ ] Setup projeto React com Vite + TypeScript
- [ ] Configurar Tailwind CSS
- [ ] Implementar autenticação (login/registro)
- [ ] Criar serviço de API
- [ ] Implementar upload de arquivo com progresso
- [ ] Criar componentes de métricas
- [ ] Implementar gráficos (Recharts)
- [ ] Adicionar React Query para cache
- [ ] Implementar histórico de uploads
- [ ] Testes (Vitest + Testing Library)
- [ ] Build e deploy

---

**Tempo estimado de migração:** 3-5 dias (1 desenvolvedor front-end experiente)
