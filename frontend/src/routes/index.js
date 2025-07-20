import { lazy } from 'react'

const Dashboard = lazy(() => import('../pages/Dashboard'))
const Forms = lazy(() => import('../pages/Forms'))
const Cards = lazy(() => import('../pages/Cards'))
const Charts = lazy(() => import('../pages/Charts'))
const Buttons = lazy(() => import('../pages/Buttons'))
const Modals = lazy(() => import('../pages/Modals'))
const Tables = lazy(() => import('../pages/Tables'))
const Page404 = lazy(() => import('../pages/404'))
const Blank = lazy(() => import('../pages/Blank'))
const GameSearch = lazy(() => import('../pages/GameSearch'))
const MyLibrary = lazy(() => import('../pages/MyLibrary'))
const Wishlist = lazy(() => import('../pages/Wishlist'))
const GameExplorer = lazy(() => import('../pages/GameExplorer'))
const SyncJobs = lazy(() => import('../pages/SyncJobs'))
const Companies = lazy(() => import('../pages/Companies'))
const Genres = lazy(() => import('../pages/Genres'))
const GameModes = lazy(() => import('../pages/GameModes'))

/**
 * ⚠ These are internal routes!
 * They will be rendered inside App.js, using the default layout
 * If you want to add a route to, let's say, a landing page, you should add
 * it to the public routes, exactly the way it was done with the login
 */
const routes = [
  {
    path: '/dashboard', // the url
    component: Dashboard, // view rendered
  },
  {
    path: '/library',
    component: MyLibrary,
  },
  {
    path: '/forms',
    component: Forms,
  },
  /*
  {
    path: '/cards',
    component: Cards,
  },
  {
    path: '/charts',
    component: Charts,
  },
  {
    path: '/buttons',
    component: Buttons,
  },
  {
    path: '/modals',
    component: Modals,
  },
  {
    path: '/tables',
    component: Tables,
  },
  */
  {
    path: '/404',
    component: Page404,
  },
  {
    path: '/blank',
    component: Blank,
  },
  {
    path: '/gamesearch',
    component: GameSearch,
  },
  {
    path: '/wishlist',
    component: Wishlist,
  },
  {
    path: '/gameexplorer',
    component: GameExplorer,
  },
  {
    path: '/syncjobs',
    component: SyncJobs,
  },
  {
    path: '/companies',
    component: Companies,
  },
  {
    path: '/genres',
    component: Genres,
  },
  {
    path: '/gamemodes',
    component: GameModes,
  },
]

export default routes
