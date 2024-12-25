import AsyncStorage from '@react-native-async-storage/async-storage';
import appConfig from '../config';

export const LOGIN_REQUEST = 'LOGIN_REQUEST';
export const LOGIN_SUCCESS = 'LOGIN_SUCCESS';
export const LOGIN_FAILURE = 'LOGIN_FAILURE';
export const LOGOUT_REQUEST = 'LOGOUT_REQUEST';
export const LOGOUT_SUCCESS = 'LOGOUT_SUCCESS';
export const LOGOUT_FAILURE = 'LOGOUT_FAILURE';

function requestLogin(creds: any) {
  return {
    type: LOGIN_REQUEST,
    isFetching: true,
    isAuthenticated: false,
    creds,
  };
}

export function receiveLogin(user: { id_token: any; }) {
  return {
    type: LOGIN_SUCCESS,
    isFetching: false,
    isAuthenticated: true,
    id_token: user.id_token,
  };
}

function loginError(message: any) {
  return {
    type: LOGIN_FAILURE,
    isFetching: false,
    isAuthenticated: false,
    message,
  };
}

function requestLogout() {
  return {
    type: LOGOUT_REQUEST,
    isFetching: true,
    isAuthenticated: true,
  };
}

export function receiveLogout() {
  return {
    type: LOGOUT_SUCCESS,
    isFetching: false,
    isAuthenticated: false,
  };
}

// Logs the user out
export function logoutUser() {
  return async (dispatch: (arg0: { type: string; isFetching: boolean; isAuthenticated: boolean; }) => void) => {
    dispatch(requestLogout());
    try {
      // Make the logout request
      await fetch('http://localhost:8000/logout', {
        method: 'POST',
        credentials: 'include',
      });

      // Remove the token from AsyncStorage
      await AsyncStorage.removeItem('id_token');

      // Dispatch logout success
      dispatch(receiveLogout());
    } catch (error) {
      console.error('Error during logout', error);
    }
  };
}


export function loginUser(creds: { name: any; password: any; }) {
    const config: RequestInit = {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      credentials: 'include', // Corrected type for credentials
      body: `email=${creds.name}&password=${creds.password}`, // Use correct field names
    };
  
    return async (dispatch: (arg0: { type: string; isFetching: boolean; isAuthenticated: boolean; creds?: any; message?: any; id_token?: any; }) => void) => {
      // We dispatch requestLogin to kickoff the call to the API
      dispatch(requestLogin(creds));
  
      if (process.env.NODE_ENV === "development") {
        try {
          // Ensure you're using the correct URL (based on your FastAPI docs)
          const response = await fetch('http://192.168.100.223/Account/Login', config);  // Correct URL
          const user = await response.json();
  
          if (!response.ok) {
            // If there was a problem, dispatch the error condition
            dispatch(loginError(user.message));
            return Promise.reject(user);
          }
  
          // If login was successful, set the token in AsyncStorage
          await AsyncStorage.setItem('id_token', user.id_token);
          dispatch(receiveLogin(user));
          return Promise.resolve(user);
        } catch (err) {
          console.error('Error: ', err);
          dispatch(loginError('Failed to login'));
        }
      } else {
        // If running in a non-dev environment, use a predefined token
        await AsyncStorage.setItem('id_token', appConfig.id_token);
        dispatch(receiveLogin({ id_token: appConfig.id_token }));
      }
    };
  }
  