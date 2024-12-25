import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  LOGIN_REQUEST, LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT_SUCCESS,
} from '../actions/user';

// Initial state is set with a promise that resolves to the value of token from AsyncStorage
const initialState = {
  isFetching: false,
  isAuthenticated: false,
  errorMessage: ''
};

export default function auth(state = initialState, action: { type: any; payload: any; }) {
  switch (action.type) {
    case LOGIN_REQUEST:
      return Object.assign({}, state, {
        isFetching: true,
        isAuthenticated: false,
      });

    case LOGIN_SUCCESS:
      return Object.assign({}, state, {
        isFetching: false,
        isAuthenticated: true,
        errorMessage: '',
      });

    case LOGIN_FAILURE:
      return Object.assign({}, state, {
        isFetching: false,
        isAuthenticated: false,
        errorMessage: action.payload,
      });

    case LOGOUT_SUCCESS:
      return Object.assign({}, state, {
        isAuthenticated: false,
        errorMessage: '',
      });

    default:
      return state;
  }
}

// Function to get the token from AsyncStorage and update the auth state
export const getTokenFromAsyncStorage = async () => {
  try {
    const token = await AsyncStorage.getItem('id_token');
    if (token) {
      return { isAuthenticated: true };
    }
    return { isAuthenticated: false };
  } catch (error) {
    console.error('Error getting token from AsyncStorage', error);
    return { isAuthenticated: false };
  }
};

// Dispatching action to check and set authentication status
export const checkAuthStatus = () => async (dispatch: (arg0: { type: string; payload?: string; }) => void) => {
  const { isAuthenticated } = await getTokenFromAsyncStorage();
  if (isAuthenticated) {
    dispatch({ type: LOGIN_SUCCESS });
  } else {
    dispatch({ type: LOGIN_FAILURE, payload: 'No token found' });
  }
};
