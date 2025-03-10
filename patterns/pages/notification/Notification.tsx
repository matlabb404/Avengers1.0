import React from 'react';
import { View, Text } from 'react-native';
import { Calendar } from 'react-native-calendars';
import styles from './Notifications.style';


class Notification extends React.Component {
  render() {
    return (
      <View style={{height:'100%'}}>
        <View style={{width: "100%"}}>
        <Text style={styles.headerText}>Notifications</Text>
        </View>
      </View>
    );
  }
}

export default Notification;
