import React from "react";

import styles from "./Footer.style";
import { View, Text } from "react-native";

class Footer extends React.Component {
  render() {
    return (
      <View style={styles.mainfoot}>
        <View style={styles.iconContainer}> 
            <Text>Home</Text>
            <Text>Home</Text>
            <Text>Post</Text>
            <Text>Search</Text>
            <Text>Profile</Text>
        </View>
    </View>
    );
  }
}

export default Footer;