import React, { Dispatch } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ActivityIndicator, View, TouchableOpacity } from 'react-native';
// import Icon from 'react-native-vector-icons/FontAwesome'; // Make sure you install this library

import Login from '../pages/login/Login';
import Register from '../pages/register/Register';
import { logoutUser } from '@/actions/user';
import { connect } from 'react-redux';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator();

interface PrivateRouteProps {
  navigation: any;
  component: React.ComponentType<any>;
}

const PrivateRoute = ({ component: Component, navigation, ...rest }: PrivateRouteProps) => {
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    const checkAuth = async () => {
      const token = await AsyncStorage.getItem('id_token');
      setIsAuthenticated(token ? true : false);
    };
    checkAuth();
  }, []);

  if (isAuthenticated === null) {
    // Show a loading spinner while checking authentication
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#0000ff" />
      </View>
    );
  }

  return isAuthenticated ? <Component {...rest} /> : null;
};

// Define the CloseButton component with TouchableOpacity and react-native-vector-icons

const CloseButton = ({ closeToast }: { closeToast: () => void }) => (
  <TouchableOpacity onPress={closeToast}>
    {/* <Icon name="close" size={20} /> */}
  </TouchableOpacity>
);

class Home extends React.PureComponent<any> {
  render() {
    return (
        <Stack.Navigator initialRouteName="Login"  screenOptions={{
          headerShown: false, // Disable headers globally
        }}>
          <Stack.Screen name="Login" component={Login} />
          <Stack.Screen name="Register" component={Register} />
          {/* Example of private route */}
          {/* <Stack.Screen
            name="Home"
            children={(props) => (
              <PrivateRoute {...props} component={HomeScreen} />
            )}
          /> */}
          {/* <Stack.Screen name="Error" component={ErrorPage} /> */}
        </Stack.Navigator>
    );
  }
}

const mapStateToProps = (state: any) => ({
  isAuthenticated: state.auth.isAuthenticated,
});

const mapDispatchToProps = (dispatch: any) => ({
  logoutUser: () => dispatch(logoutUser()),
});

export default connect(mapStateToProps)(Home);
