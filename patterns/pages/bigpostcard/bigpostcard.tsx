import React from "react";
import styles from "./bigpostcard.style";
import { View, Text, Image, ScrollView, TouchableOpacity } from "react-native";

interface Post {
    id: string;
    name: string;
    description: string;
    review: number;
    picture_url?: string | string[];
    aspectRatio: number | null;
}

const BigPostCard = ({ route }: { route: { params: Post } }) => {
    const { id, name, description, review, picture_url, aspectRatio } = route.params;
    
    const pictureCount = Array.isArray(picture_url)
        ? picture_url.filter((url) => url.trim() !== '').length
        : 0;

    return (
        pictureCount === 0 ? (
            <View style={styles.maincard}>
                <View style={styles.mainpost}>
                    <View style={styles.namecontainer}>
                        <Text style={styles.vendorname}>{name}</Text>
                    </View>
                    <View style={styles.descriptionbox}>
                        <Text>{description}</Text>
                    </View>
                    {/* Rating */}
                    <View style={styles.reviews}>
                        <Text style={{ textAlign: 'right' }}>{review} Reviews</Text>
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
            </View>
        ) : (
            <View style={styles.maincard}>
                <View style={styles.mainpost}>
                    <View style={styles.namecontainer}>
                        <Text style={styles.vendorname}>{name}</Text>
                    </View>
                    <View style={styles.descriptionbox}>
                        <Text>{description}</Text>
                    </View>
                    <View style={styles.mediaconatinaer}>
                        {/* Render media only if there's exactly one image */}
                        {Array.isArray(picture_url) && picture_url.filter((url) => url.trim() !== '').length === 1 ? (
                            <View style={{ flex: 1, width: '100%', height: undefined }}>
                                <Image
                                    source={{ uri: picture_url[0] }}
                                    style={{
                                        width: '100%',
                                        height: undefined, // Use dynamic height
                                        aspectRatio: aspectRatio,
                                        resizeMode: 'contain',
                                    }}
                                />
                            </View>
                        ) : (
                            <ScrollView horizontal showsHorizontalScrollIndicator={false}
                            //   contentContainerStyle={{ justifyContent: 'space-between', gap: 10 }}
                            >
                                {Array.isArray(picture_url) &&
                                    picture_url.map((url, index) => (
                                        <View key={index} style={styles.mediaImage}>
                                            <Image source={{ uri: url }} style={{
                                                width: '100%',
                                                height: undefined, // Use dynamic height
                                                aspectRatio: aspectRatio,
                                                resizeMode: 'contain',
                                            }} />
                                        </View>
                                    ))
                                }
                            </ScrollView>
                        )}
                    </View>
                    {/* Rating */}
                    <View style={styles.reviews}>
                        <Text style={{ textAlign: 'right' }}>{review} Reviews</Text>
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
            </View >
        )
    );
}

export default BigPostCard;