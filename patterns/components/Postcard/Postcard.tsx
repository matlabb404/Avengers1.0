import React, { Component, useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView, Image, Dimensions, Animated } from 'react-native';
import styles from './Postcard.style';
import BigPostCard from '../bigpostcard/bigpostcard';


interface Post {
  id: any;
  name: string;
  description: string;
  review: number;
  picture_url?: string | string[];
  aspectRatio: number | null;
}

interface PostCardProps {
  post: Post;
  navigation: any;
}


interface PostCardState {
  fullscreen: boolean;
  isExpanded: boolean;
  imageRatio: number | null;
  imageHeight: number; // Add imageHeight to the state interface
}


class PostCard extends Component<PostCardProps, PostCardState> {
  // Animated value to control the height of the dropdown
  animatedValue = new Animated.Value(0); // Moved to class level to avoid unnecessary reinitialization
  constructor(props: PostCardProps) {
    super(props);
    this.state = {
      fullscreen: false,
      isExpanded: false,
      imageRatio: null,
      imageHeight: 0,  // To store image height when there's only one image
    };
  }  

  setModalVisible = (visible: boolean) => {
    this.setState({ fullscreen: visible });
  };

  toggleExpanded = () => {
    this.setState((prevState) => ({
      isExpanded: !prevState.isExpanded,
    }));
  };

  componentDidMount() {
    const { post } = this.props;

    // If there's exactly one picture, we fetch its height
    if (Array.isArray(post.picture_url) && post.picture_url.length === 1) {
      this.fetchImageHeight(post.picture_url[0]);
    }
  }

  fetchImageHeight = (imageUrl: string) => {
    Image.getSize(
      imageUrl,
      (width, height) => {
        const screenWidth = Dimensions.get('window').width;
        // const calculatedHeight = ((width / height) < 1 ) ? (height / width) * screenWidth * 0.9 : (height / width) * screenWidth * 0.97; // Adjust for screen width
        const calculatedHeight = (height / width) * screenWidth * 0.9 * 0.96; // Adjust for screen width
        console.log('Calculated Image Height and ratio:', calculatedHeight, width / height); // Log the correct value
        console.log('screenwidth:', screenWidth); // Log the correct value
        this.setState({
          imageHeight: calculatedHeight,
          imageRatio: width / height
        });
      },
    );
  };

  expandPost = (items: Post) => {
    // console.log('Pressed Post: ', post);
    // navigation.navigate('Expanded',post);
    this.setState({ fullscreen: true });
  };
  
  showanimatedview = (items: Post) => {
    return <BigPostCard post={items} modalVisible={this.state.fullscreen} setModalVisible={this.setModalVisible}/>;
  };

  render() {
    const { post, navigation } = this.props;
    const { isExpanded, imageHeight, fullscreen } = this.state;

    // Check the number of non-empty image URLs
    const pictureCount = Array.isArray(post.picture_url)
      ? post.picture_url.filter((url) => url.trim() !== '').length
      : 0;

    // Dynamically adjust the description box height if there is exactly one image
    const descriptionStyle = pictureCount === 1 && imageHeight > 0
      ? { minHeight: imageHeight + 15, maxHeight: imageHeight + 15, marginBottom: 0, position: 'absolute' }
      : {
        height: 210,
        maxHeight: 210,
        marginBottom: -160,
        paddingTop: 3,
        paddingBottom: 3,
      };

    ///////////////////////////   ANIMATIONS    ////////////////////

    // const dynamicMainPost = {
    //   flex: 1,
    //   width: this.animatedValue.interpolate({
    //     inputRange: [0, 1],
    //     outputRange: ['100%', '90%']
    //   }),
    //   height: this.animatedValue.interpolate({
    //     inputRange: [0, 1],
    //     outputRange: ['100%', '90%']
    //   }),
    //   // position: 0,
    //   zIndex: 60,
    //   position: 'absolute',
    //   left: 0,
    //   right: 0,
    //   marginRight: 0,
    //   marginLeft: 0,
    //   padding: 0,
    //   // iOS Shadow
    //   shadowColor: 'transparent',
    //   shadowOffset: { width: 0, height: 0 },
    //   shadowOpacity: 0,
    //   shadowRadius: 0,
    //   // Android Shadow
    //   elevation: 0,
    // };

    ///////////////////////////  ANIMATIONS END  ////////////////////

    return (
      <Animated.View style={styles.maincard} onTouchEnd={() => this.expandPost(post)}>

      {fullscreen? this.showanimatedview(post):null}

      {/* end of animated views  */}


        {pictureCount === 0 ? (
          <View style={{ flex: 1 }}>
            {/* Name */}
            <View style={styles.namecontainer}>
              <Text style={styles.vendorname}>{post.name}</Text>
            </View>

            {/* Description */}
            <View style={{ marginTop: 0 }}>
              <ScrollView
                style={styles.descriptionboxexpandeddefault}
                nestedScrollEnabled={true}
                showsVerticalScrollIndicator={false}
              >
                <Text>{post.description}</Text>
              </ScrollView>
            </View>

            {/* Rating */}
            <View style={styles.reviews}>
              <Text style={{ textAlign: 'right' }}>{post.review} Reviews</Text>
            </View>

            {/* Footer Actions */}
            <View style={styles.iconcontainer}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <TouchableOpacity>
                  <Text>Comment</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Share</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Reply</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Bookmark</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Book</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        ) : (
          <View style={{ flex: 1 }}>
            {/* Name */}
            <View style={styles.namecontainer}>
              <Text style={styles.vendorname}>{post.name}</Text>
            </View>

            {/* Description */}
            <View style={{ flex: 1 }}>
              <View style={{ marginTop: 0 }}>
                {isExpanded ? (
                  <ScrollView
                    style={[styles.descriptionboxexpanded, descriptionStyle]} // Apply height conditionally
                    nestedScrollEnabled={true}
                    showsVerticalScrollIndicator={false}
                  >
                    <Text>{post.description}</Text>
                    <View style={styles.buttonbox}>
                      <TouchableOpacity onPress={this.toggleExpanded}>
                        <Text style={styles.readMoreExpanded}>
                          {isExpanded ? 'Show Less' : 'Read More...'}
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </ScrollView>
                ) : (
                  <View style={[styles.descriptionbox]}>
                    <Text numberOfLines={2}>{post.description}</Text>
                    <View style={styles.buttonbox}>
                      <TouchableOpacity onPress={this.toggleExpanded}>
                        <Text style={styles.readMore}>
                          {isExpanded ? 'Show Less' : 'Read More...'}
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </View>

              {/* Media */}
              <View style={styles.mediaconatinaer}>
                {/* Render media only if there's exactly one image */}
                {Array.isArray(post.picture_url) && post.picture_url.filter((url) => url.trim() !== '').length === 1 ? (
                  <View style={{ flex: 1, width: '100%', height: undefined }}>
                    <Image
                      source={{ uri: post.picture_url[0] }}
                      style={{
                        width: '100%',
                        height: undefined, // Use dynamic height
                        aspectRatio: this.state.imageRatio,
                        resizeMode: 'contain',
                      }}
                    />
                  </View>
                ) : (
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ justifyContent: 'space-between', gap: 10 }}>
                    {Array.isArray(post.picture_url) &&
                      post.picture_url.map((url, index) => (
                        <View key={index} style={styles.mediaImage}>
                          <Image source={{ uri: url }} style={{ width: '100%', height: '100%' }} />
                        </View>
                      ))
                    }
                  </ScrollView>
                )}
              </View>
            </View>

            {/* Rating */}
            {Array.isArray(post.picture_url) && post.picture_url.filter((url) => url.trim() !== '').length === 1 ? (
              <View style={[styles.reviews, { height: isExpanded ? 72 : 22, paddingTop: isExpanded ? 50 : 0, }]}>
                <Text style={{ textAlign: 'right' }}>{post.review} Reviews</Text>
              </View>
            ) : (
              <View style={styles.reviews}>
                <Text style={{ textAlign: 'right' }}>{post.review} Reviews</Text>
              </View>
            )}

            {/* Footer Actions */}
            <View style={styles.iconcontainer}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <TouchableOpacity>
                  <Text>Comment</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Share</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Reply</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Bookmark</Text>
                </TouchableOpacity>
                <TouchableOpacity>
                  <Text>Book</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}
    </Animated.View>
    );
  }
}

export default PostCard;


// i know i know just correct what you will and move on!!!!you can email me after yawdjandanquah@gmail.com 