import React, { Dispatch, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ActivityIndicator, View, TouchableOpacity } from 'react-native';
// import Icon from 'react-native-vector-icons/FontAwesome'; // Uncomment if using this library
import { connect } from 'react-redux';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import Login from '../pages/login/Login';
import Register from '../pages/register/Register';
import HomeScreen from '../pages/homescreen/Homescreen';
import Following from '@/pages/follow/Follow';
import Discover from '@/pages/discover/Discover';

import { logoutUser } from '@/actions/user';

const Stack = createNativeStackNavigator();

const AppNavigator = ({ isAuthenticated }: { isAuthenticated: boolean }) => {
  const [isLoading, setIsLoading] = React.useState(true);
  const [initialRoute, setInitialRoute] = React.useState<string>('Login');

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = await AsyncStorage.getItem('id_token');
        if (token) {
          setInitialRoute('Main');
        }
      } catch (error) {
        console.error('Error checking authentication:', error);
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  if (isLoading) {
    // Show a loading spinner while checking authentication
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#0000ff" />
      </View>
    );
  }

  return (
    <Stack.Navigator
      initialRouteName={initialRoute}
      screenOptions={{
        headerShown: false, // Disable headers globally
      }}
    >
      <Stack.Screen name="Login" component={Login} />
      <Stack.Screen name="Register" component={Register} />
      <Stack.Screen name="Following" component={Following} />
      <Stack.Screen name="Discover" component={Discover} />
      <Stack.Screen name="Main" component={HomeScreen} />
    </Stack.Navigator>
  );
};

// Define the CloseButton component with TouchableOpacity and react-native-vector-icons
const CloseButton = ({ closeToast }: { closeToast: () => void }) => (
  <TouchableOpacity onPress={closeToast}>
    {/* <Icon name="close" size={20} /> */}
  </TouchableOpacity>
);

const Home = (props: any) => {
  return (
      <AppNavigator isAuthenticated={props.isAuthenticated} />
  );
};

const mapStateToProps = (state: any) => ({
  isAuthenticated: state.auth.isAuthenticated,
});

const mapDispatchToProps = (dispatch: any) => ({
  logoutUser: () => dispatch(logoutUser()),
});

export default connect(mapStateToProps, mapDispatchToProps)(Home);
