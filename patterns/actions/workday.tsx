// import AsyncStorage from '@react-native-async-storage/async-storage';
// import appConfig from '../config';

// export const CREATE_LOG_INITIAL = 'CREATE_LOG_INITIAL';
// export const CREATE_LOG_REQUEST = 'CREATE_LOG_REQUEST';
// export const CREATE_LOG_SUCCESS = 'CREATE_LOG_SUCCESS';
// export const CREATE_LOG_FAILURE = 'CREATE_LOG_FAILURE';
// export const FETCH_LOG_REQUEST = 'FETCH_LOG_REQUEST';
// export const FETCH_LOG_SUCCESS = 'FETCH_LOG_SUCCESS';
// export const FETCH_LOG_FAILURE = 'FETCH_LOG_FAILURE';
// export const LOGIN_SUCCESS = 'LOGIN_SUCCESS';

// function createLogInitial() {
//   return {
//     type: CREATE_LOG_INITIAL,
//     isFetching: false,
//   };
// }

// function requestCreateLog(log: any) {
//   return {
//     type: CREATE_LOG_REQUEST,
//     isFetching: true,
//     log,
//   };
// }

// function createLogSuccess(log: any) {
//   return {
//     type: CREATE_LOG_SUCCESS,
//     isFetching: false,
//     log,
//   };
// }

// export function receiveLogin(user: { id_token: any; }) {
//   return {
//     type: LOGIN_SUCCESS,
//     isFetching: false,
//     isAuthenticated: true,
//     id_token: user.id_token,
//   };
// }

// function createLogError(message: string) {
//   return {
//     type: CREATE_LOG_FAILURE,
//     isFetching: false,
//     message,
//   };
// }

// function requestFetchLog() {
//   return {
//     type: FETCH_LOG_REQUEST,
//     isFetching: true,
//   };
// }

// function fetchLogSuccess(log: any) {
//   return {
//     type: FETCH_LOG_SUCCESS,
//     isFetching: false,
//     log,
//   };
// }

// function fetchLogError(message: any) {
//   return {
//     type: FETCH_LOG_FAILURE,
//     isFetching: false,
//     message,
//   };
// }
// interface WorkDayLogData {
//   userId: string;
//   inputKilograms?: number;
//   KilogramperPeice?: number;
//   inputPieces?: number;
//   tonnes?: number;
//   outputGrams: number;
//   expected: number; //required defaults to 10
//   //outputNumber?: number;
//   outputString: string;
//   enteredAt?: Date; // required should be input automatically
// }

// export function createWorkDayLog(logData: WorkDayLogData) {
//   const config: RequestInit = {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
//     credentials: 'include',
//     body: `userId=${logData.userId}&inputKilograms=${logData.inputKilograms}&KilogramperPeice=${logData.KilogramperPeice}&inputPieces=${logData.inputPieces}&tonnes=${logData.tonnes}&outputGrams=${logData.outputGrams}&expected=${logData.expected}&outputString=${logData.outputString}`,
//   };

//   return async (dispatch: (arg0: { type: string; isFetching: boolean; log?: any; message?: any; }) => void) => {
//     // We dispatch requestCreatePost to kickoff the call to the API
//     dispatch(requestCreateLog(logData));

//     if (process.env.NODE_ENV === "development") {
//       try {
//         const response = await fetch('http://localhost:5000/logworkday', config);
//         const wdl = await response.json();

//         if (!response.ok) {
//           // If there was a problem, dispatch the error condition
//           dispatch(createLogError(wdl.message));
//           return Promise.reject(wdl);
//         }

//         await AsyncStorage.setItem('id_token', wdl.id_token);
//         // Dispatch the success action
//         dispatch(receiveLogin(wdl));
//         return Promise.resolve(wdl);
//       } catch (err) {
//         console.error('Error: ', err);
//         dispatch(createLogError('Failed to login'));
//       }
//     } else {
//       // If running in a non-dev environment, use a predefined token
//       await AsyncStorage.setItem('id_token', appConfig.id_token);
//       dispatch(receiveLogin({ id_token: appConfig.id_token }));
//     }
//   };
// }

// export function fetchLog() {
//   const config = {
//     method: 'post',
//     headers: {
//       Accept: 'application/json',
//       'Content-Type': 'application/json',
//     },
//     body: JSON.stringify({
//       query: '{workday{workDayId,userId,inputKilograms,KilogramperPeice,inputPieces,tonnes,outputGrams,expected,outputString,enteredAt}}',
//     }),
//     credentials: 'include',
//   };

//   return async (dispatch: (arg0: { type: string; isFetching: boolean; message?: any; log?: any; }) => void) => {
//     dispatch(requestFetchLog());

//     try {
//       // Step 1: Fetch the response
//       const response = await fetch('http://localhost:5000/graphql', config);
//       const wdl = await response.json(); // Parse JSON

//       // Step 2: Extract data
//       const ne_workday = wdl?.data?.workday; // Safely access `workday`

//       // Step 3: Check for errors
//       if (!ne_workday) {
//         // Dispatch an error action if workday is missing
//         const errorMessage = wdl?.errors?.[0]?.message || 'Error fetching workday data';
//         dispatch(fetchLogError(errorMessage));
//         throw new Error(errorMessage); // Stop execution and throw error
//       }

//       const workday = await Promise.all(
//         ne_workday.map(async (log) => {
//           // Fetch the name for each log
//           const nameResponse = await fetch(`http://localhost:5000/username?name=${encodeURIComponent(log.userId)}`);

//           const nameData = await nameResponse.json();
          
          
//           return {
//             ...log,
//             name: nameData, // Add the name field
//             enteredAt: new Date(Number(log.enteredAt)).toLocaleString(),// Format it as a string
//           };
//         })
//       );

//       // Step 4: Dispatch success action
//       dispatch(fetchLogSuccess(workday));
//       console.log('told me',workday);
//       return workday; // Return the data for further use if needed
//     } catch (error) {
//       console.error('Error fetching logs:', error);
//       throw error; // Re-throw the error for further handling if needed
//     }
//   }
// }
