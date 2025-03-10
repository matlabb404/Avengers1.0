import React from "react";
import { View, TextInput, TouchableOpacity, Text, SafeAreaView } from "react-native";
import { connect } from "react-redux";
import PropTypes from "prop-types";
import { loginUser } from "../../actions/user"; // assuming you have this action
import AsyncStorage from "@react-native-async-storage/async-storage";
import styles from "./Login.module";
import jwtDecode from "jwt-decode";
import config from "../../config";

// TypeScript types for props and state
interface LoginProps {
  navigation: any;
  dispatch: any;
  isFetching: boolean;
  isAuthenticated: boolean;
}

interface LoginState {
  login: string;
  password: string;
  showPassword: boolean; // Add this to manage password visibility
  errorMessage: string | null;
}

class Login extends React.Component<LoginProps, LoginState> {
  constructor(props: LoginProps) {
    super(props);
    this.state = {
      login: "",
      password: "",
      showPassword: false, // Initialize showPassword to false
    };
  }

  // Methods to handle login and password changes
  handleLoginChange = (login: string) => {
    this.setState({ login });
  };

  handlePasswordChange = (password: string) => {
    this.setState({ password });
  };

  // Method to toggle password visibility
  togglePasswordVisibility = () => {
    this.setState((prevState) => ({ showPassword: !prevState.showPassword }));
  };

  // Method to handle login button press
  doLogin = async () => {
    const { login, password } = this.state;
    const { dispatch } = this.props;
    this.setState({ errorMessage: "" });
  
    // Dispatch the login action
    try {
      await dispatch(loginUser({ name: login, password })); // Wait for the login action to complete
  
      if (this.props.isAuthenticated) {
        // Navigate to the main screen if login is successful
        this.props.navigation.navigate("HomeScreen");
      } else {
        // Display an error message if authentication fails
      }
    } catch (error) {
      this.setState({ errorMessage: "Please check email or password." });
      // Handle any errors during login
    }
  };

  render() {
    const { login, password, showPassword, errorMessage } = this.state;
    const { isFetching, navigation } = this.props;

    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.title}>Login to your App</Text>


        <TextInput
          style={styles.input}
          value={login}
          onChangeText={this.handleLoginChange}
          placeholder="Email"
          autoCapitalize="none"
          />

        <View style={styles.passwordContainer}>
          <TextInput
            style={styles.password}
            value={password}
            onChangeText={this.handlePasswordChange}
            placeholder="Password"
            secureTextEntry={!showPassword} // Toggle secureTextEntry
            />
          <TouchableOpacity
            style={styles.toggleButton}
            onPress={this.togglePasswordVisibility} // Call togglePasswordVisibility
            >
            <Text style={styles.toggleText}>{showPassword ? "Hide" : "Show"}</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={styles.button}
          onPress={this.doLogin}
          disabled={isFetching}
          >
          <Text style={styles.text}>{isFetching ? "Loading..." : "Login"}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.button}
          onPress={() => navigation.navigate("Register")} // Navigate to Register screen
          >
          <Text style={styles.text}>Create an account</Text>
        </TouchableOpacity>
        {errorMessage && <Text style={styles.error}>{errorMessage}</Text>}
      </SafeAreaView>
    );
  }
}

// Map state from Redux store to component props
const mapStateToProps = (state: {
  auth: { isFetching: boolean; isAuthenticated: boolean; errorMessage: string };
}) => ({
  isFetching: state.auth.isFetching,
  isAuthenticated: state.auth.isAuthenticated,
  errorMessage: state.auth.errorMessage,
});

export default connect(mapStateToProps)(Login);
