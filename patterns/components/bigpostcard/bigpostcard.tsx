import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  Image,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  Modal,
  Animated,
} from "react-native";
import styles from "./bigpostcard.style";

import Footer from "../Footer/Footer";

interface Post {
  id: string;
  name: string;
  description: string;
  review: number;
  picture_url?: string[];
}

const BigPostCard: React.FC<any> = ({
  post,
  modalVisible,
  setModalVisible,
}: {
  post: Post;
  modalVisible: boolean;
  setModalVisible: (visible: boolean) => void;
}) => {
  const [imageHeight, setImageHeight] = useState<number | null>(null);
  const screenWidth = Dimensions.get("window").width;
  const animatedWidth = useRef(new Animated.Value(screenWidth * 0.9)).current;
  const animatedMargin = useRef(new Animated.Value(screenWidth * 0.05)).current;
  const animatedNameHeight = useRef(new Animated.Value(20)).current;

  useEffect(() => {
    if (post.picture_url && post.picture_url.filter((url) => url.trim() !== "").length > 0) {
      let maxHeight = 0;
      post.picture_url
        .filter((url) => url.trim() !== "") // Filter out empty strings
        .forEach((url) => {
          Image.getSize(
            url,
            (width, height) => {
              const calculatedHeight = (height / width) * screenWidth;
              if (calculatedHeight > maxHeight) {
                maxHeight = calculatedHeight;
                setImageHeight(maxHeight); // Update state with the maximum height
              }
            },
          );
        });
    }    
  }, [post.picture_url]);

  // Animation effect when modal visibility changes
  useEffect(() => {
    if (modalVisible) {
      Animated.parallel([
        Animated.timing(animatedWidth, {
          toValue: screenWidth,
          duration: 300,
          useNativeDriver: false,
        }),
        Animated.timing(animatedMargin, {
          toValue: 0,
          duration: 300,
          useNativeDriver: false,
        }),
        Animated.timing(animatedNameHeight, {
          toValue: 40,
          duration: 300,
          useNativeDriver: false,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(animatedWidth, {
          toValue: screenWidth,
          duration: 300,
          useNativeDriver: false,
        }),
        Animated.timing(animatedMargin, {
          toValue: 0,
          duration: 300,
          useNativeDriver: false,
        }),
        Animated.timing(animatedNameHeight, {
          toValue: 40,
          duration: 300,
          useNativeDriver: false,
        }),
      ]).start();
    }
  }, [modalVisible]);

  const renderFooterActions = () => (
    <View style={styles.iconcontainer}>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        {["Comment", "Share", "Reply", "Bookmark", "Book"].map((action, index) => (
          <TouchableOpacity key={index}>
            <Text>{action}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  const renderImages = () => {
    if (!post.picture_url || !imageHeight ) {
      return null;
    } else if (post.picture_url.length === 1) {
      return (
        <Image
          source={{ uri: post.picture_url[0] }}
          style={{
            width: "100%",
            height: imageHeight || 200, // Use calculated height or fallback
            resizeMode: "contain",
          }}
        />
      );
    } else {
      return (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {post.picture_url.map((url, index) => (
            <View key={index} style={[styles.mediaImage, { width: screenWidth, height: imageHeight }]}>
              <Image
                source={{ uri: url }}
                style={{
                  flex: 1,
                  width: screenWidth,
                  height: undefined, // Default height for multiple images
                  resizeMode: "contain",
                }}
              />
            </View>
          ))}
        </ScrollView>
      );
    }
  };

  ///////////////////////////Animated Styles///////////////////////////
  const dynamicMainCard = {
    width: animatedWidth,
    marginLeft: animatedMargin,
    marginRight: animatedMargin,
  };

  const dynamicNameContainer = {
    width: animatedWidth,
    height: animatedNameHeight,
  };

  const dynamicDescriptionBox = {
    width: animatedWidth,
  };

  return (
    <Modal
      visible={modalVisible}
      onRequestClose={() => setModalVisible(false)}
    >
      <ScrollView showsVerticalScrollIndicator>
        <Animated.View style={[styles.maincard, dynamicMainCard]}>
          {/* Header */}
          <Animated.View style={[styles.namecontainer, dynamicNameContainer]}>
            <Text style={styles.vendorname}>{post.name}</Text>
          </Animated.View>

          {/* Description */}
          <Animated.View style={[styles.descriptionbox, dynamicDescriptionBox]}>
            <Text>{post.description}</Text>
          </Animated.View>

          {/* Media */}
          <View style={styles.mediaconatinaer}>{renderImages()}</View>

          {/* Reviews */}
          <View style={styles.reviews}>
            <Text style={{ textAlign: "right" }}>{post.review} Reviews</Text>
          </View>

          {/* Footer Actions */}
          {renderFooterActions()}
        </Animated.View>
      </ScrollView>
    </Modal>
  );
};

export default BigPostCard;
