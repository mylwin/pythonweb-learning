import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './store'
import { setupI18n } from './i18n'
import { useThemeStore } from './store/theme'

// 导入Vant组件库
import {
  Button,
  NavBar,
  Tabbar,
  TabbarItem,
  Tab,
  Tabs,
  List,
  PullRefresh,
  Cell,
  CellGroup,
  Grid,
  GridItem,
  Empty,
  Form,
  Field,
  Image,
  Toast,
  Icon,
  Popup,
  Radio,
  RadioGroup,
} from 'vant'

// 导入Vant样式
import 'vant/lib/index.css'

// 导入全局样式
import './style.css'

const app = createApp(App)

// 设置i18n
const i18n = setupI18n()
app.use(i18n)

// 注册Vant组件
app.use(Button)
app.use(NavBar)
app.use(Tabbar)
app.use(TabbarItem)
app.use(Tab)
app.use(Tabs)
app.use(List)
app.use(PullRefresh)
app.use(Cell)
app.use(CellGroup)
app.use(Grid)
app.use(GridItem)
app.use(Empty)
app.use(Form)
app.use(Field)
app.use(Image)
app.use(Toast)
app.use(Icon)
app.use(Popup)
app.use(Radio)
app.use(RadioGroup)

// pinia 必须先于 router 安装，路由守卫里才能使用 store
app.use(pinia)
app.use(router)

// 挂载前应用已保存的主题，避免首屏闪烁
useThemeStore().initTheme()

app.mount('#app')
