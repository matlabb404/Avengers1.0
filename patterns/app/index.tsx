import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import {thunk} from 'redux-thunk';

import Home from '../components/App'; // Ensure path correctness
import combineReducers from '../reducers'; // Make sure this points to your combined reducers

// Create Redux store
const store = configureStore({ reducer: combineReducers, middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(thunk) });

export default function App() {
  return (
    <Provider store={store} >
      <Home screenOptions={{
          headerShown: false, // This hides the header for all screens
        }}/>
    </Provider>
  );
} 
