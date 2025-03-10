import React from "react";
import { View, Text, TouchableOpacity, SafeAreaView } from "react-native";

import styles from "./Footer.style";

interface FooterProps {
  activePage: string;
  onNavigate: (newActiveComp: string, newActivePage?: string) => void;
}


const Footer = ({ activePage, onNavigate }: FooterProps) => {

  return (
    <SafeAreaView style={styles.mainfoot}>
      <View style={styles.iconContainer}>
        <TouchableOpacity onPress={() => onNavigate("HomeScreen")}><Text>Home</Text></TouchableOpacity>
        <TouchableOpacity><Text style={activePage === "HomeScreen" ? styles.activeText : styles.inactiveText}>Home</Text></TouchableOpacity>
        <TouchableOpacity onPress={() => onNavigate("Post")}>
          <Text style={activePage === "Post" ? styles.activeText : styles.inactiveText}>
            Post
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => onNavigate("Search")}>
          <Text style={activePage === "Search" ? styles.activeText : styles.inactiveText}>
            Search
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => onNavigate("Profile")}>
          <Text style={activePage === "Profile" ? styles.activeText : styles.inactiveText}>
            Profile
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

export default Footer;