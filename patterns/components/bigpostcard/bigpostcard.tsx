import React, { useEffect, useRef, useState } from "react";
import { View, Text, Image, ScrollView, TouchableOpacity, Dimensions, Modal, BackHandler, Animated } from "react-native";
import styles from "./bigpostcard.style";

import Footer from "../Footer/Footer";

interface Post {
  id: string;
  name: string;
  description: string;
  review: number;
  picture_url?: string[];
}

const BigPostCard: React.FC<any> = ({ post, modalVisible, setModalVisible }: { post: Post, modalVisible: boolean, setModalVisible: (visible: boolean) => void; }) => {
  //   console.log("Post after pressed: ", post);

  const [imageHeight, setImageHeight] = useState<number | null>(null);
  const screenWidth = Dimensions.get("window").width;
  const screenHeight = Dimensions.get("window").height;
  const animatedValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (post.picture_url && post.picture_url.length > 0) {
      let maxHeight = 0;
      post.picture_url.forEach((url) => {
        Image.getSize(
          url,
          (width, height) => {
            const calculatedHeight = (height / width) * screenWidth;
            if (calculatedHeight > maxHeight) {
              maxHeight = calculatedHeight;
              setImageHeight(maxHeight); // Update state with the maximum height
            }
          },
          (error) => console.error("Failed to fetch image size: ", error)
        );
      });
    }
  }, [post.picture_url]);

  const fetchImageHeight = (imageUrl: string) => {
    Image.getSize(
      imageUrl,
      (width, height) => {
        const calculatedHeight = (height / width) * screenWidth;
        setImageHeight(calculatedHeight); // Update state with the calculated height
      },
      (error) => console.error("Failed to fetch image size: ", error)
    );
  };

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
    if (!post.picture_url || post.picture_url.length === 0) {
      return null;
    }
    else if (post.picture_url.length === 1) {
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
  const dynamicmaincard = {
    width: animatedValue.interpolate({
      inputRange: [0, 1],
      outputRange: ['100%', '90%'],
      extrapolate: "clamp",
    }),
    marginRight: animatedValue.interpolate({
      inputRange: [0, 1],
      outputRange: ['0%', '5%'],
      extrapolate: "clamp",
    }),
    marginLeft: animatedValue.interpolate({
      inputRange: [0, 1],
      outputRange: ['0%', '5%'],
      extrapolate: "clamp",
    }),
    // display: 'flex',
    // flexDirection: 'column',
    // marginBottom: 11,
    // marginTop: 9,
    // backgroundColor: theme.colors.primary,
    // borderRadius: theme.sizes.medium,
    // padding: theme.sizes.xsmall,
  };

  const dynamicnamecontainer = {
    width: animatedValue.interpolate({
      inputRange: [0, 1],
      outputRange: ['96%', '100%'],
      extrapolate: "clamp",
    }),
    height: animatedValue.interpolate({
      inputRange: [0, 1],
      outputRange: [40, 20],
      extrapolate: "clamp",
    }),
  };

  const dynamicdescriptionbox = {
    width: animatedValue.interpolate({
      inputRange: [0, 1],
      outputRange: ['96%', '100%'],
      extrapolate: "clamp",
    }),
  };

  return (
    <Modal
      // animationType="fade"
      visible={modalVisible}
      onRequestClose={() => { setModalVisible(false); }}
    >
      <ScrollView showsVerticalScrollIndicator >
        <Animated.View style={[styles.maincard, dynamicmaincard]}>
          {/* Header */}
          <Animated.View style={[styles.namecontainer, dynamicnamecontainer]}>
            <Text style={styles.vendorname}>{post.name}</Text>
          </Animated.View>

          {/* Description */}
          <Animated.View style={[styles.descriptionbox, dynamicdescriptionbox]}>
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
