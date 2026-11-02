import { lazy } from 'react'

const Dashboard = lazy(() => import('../pages/Dashboard'))
const Page404 = lazy(() => import('../pages/404'))
const GameSearch = lazy(() => import('../pages/GameSearch'))
const MyLibrary = lazy(() => import('../pages/MyLibrary'))
const Wishlist = lazy(() => import('../pages/Wishlist'))
const GameExplorer = lazy(() => import('../pages/GameExplorer'))
const SyncJobs = lazy(() => import('../pages/SyncJobs'))
const Services = lazy(() => import('../pages/Services'))
const Settings = lazy(() => import('../pages/Settings'))
const Statistics = lazy(() => import('../pages/Statistics'))
const VerifyGames = lazy(() => import('../pages/VerifyGames'))
const GameDetail = lazy(() => import('../pages/GameDetail'))

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
    path: '/404',
    component: Page404,
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
    path: '/services',
    component: Services,
  },
  {
    path: '/settings',
    component: Settings,
  },
  {
    path: '/statistics',
    component: Statistics,
  },
  {
    path: '/verify',
    component: VerifyGames,
  },
  {
    path: '/games/:gameId',
    component: GameDetail,
  },
]

export default routes
