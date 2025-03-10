import React, { useEffect, useRef, useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    Animated,
    PanResponder,
    Dimensions,
    BackHandler,
    SafeAreaView,
} from "react-native";
import styles from "./dropdown.style";

import Notification from "@/pages/notification/Notification";
import Saved from "@/pages/saved/Saved";
import Chat from "@/pages/chat/Chat";
import Booking from "@/pages/booking/Booking";
import { connect } from "react-redux";
import { Header } from "react-native/Libraries/NewAppScreen";
import { openDropdown, closeDropdown, toggleDropdown } from "../../actions/navigation";

// Define the type for the column headers
interface ColumnHeader {
    link: string;
    value: string;
    isActive: boolean;
}

interface displaypage {
    pagedropdown: string;
}

// Props for the Dropdown component
interface DropdownState {
    belowPage: displaypage;
    activeLink: string | null;
    abovePage: string;
    animatedValues: Animated.Value; // Integer value to reflect the animation progress
    setAnimatedValues: (value: number) => void;
    setDropdownOpen: (value: boolean) => void;
}

interface MotionProps {
    headers: ColumnHeader[];
    navigation: any;
    dispatch: any;
    dropdownOpened: boolean;
    dropdownStatic: boolean;
}

class Dropdown extends React.Component<MotionProps, DropdownState> {
    touchY = React.createRef<number | null>();
    pan = new Animated.ValueXY();
    originalWidthRef = React.createRef<number | null>();
    screenHeight = Dimensions.get("window").height;
    screenWidth = Dimensions.get("window").width;
    halfScreenHeight = this.screenHeight / 2;
    shouldCollapse = false;
    panResponder: any;
    secondPanResponder: any;

    constructor(props: MotionProps) {
        super(props);
        this.state = {
            belowPage: { pagedropdown: '' },
            activeLink: null,
            abovePage: 'Notification',
            animatedValues: new Animated.Value(0),
            setAnimatedValues: (value: number) => this.setState({ animatedValues: new Animated.Value(value) }),
        };

        this.panResponder = PanResponder.create({
            onMoveShouldSetPanResponder: (_, gesture) => {
                // Disable pan handling if touch is slight or near buttons
                return Math.abs(gesture.dx) > 30 || Math.abs(gesture.dy) > 30;
            },
            onStartShouldSetPanResponderCapture: (evt, gesture) => {
                // Block pan for buttons or interactive elements
                return true;
            },
            onPanResponderGrant: () => {
                console.log("PAN RESPONDER WAS GRANTED ACCESS!!!");
                this.props.dispatch(toggleDropdown());
                this.pan.setValue({ x: 0, y: 0 }); // Prevent cumulative gesture errors
            },
            onPanResponderMove: (_, gesture) => {
                this.pan.y.setValue(gesture.dy);
            },
            onPanResponderRelease: (_, gesture) => {
                console.log(
                    { ...this.pan.y }, 'BEFORE'
                );
                this.pan.flattenOffset();
                console.log(
                    { ...this.pan.y }, 'AFTER'
                );

                const releasePoint = gesture.moveY;
                this.shouldCollapse = releasePoint > this.screenHeight / 3;

                const targetPosition = this.shouldCollapse ? this.screenHeight - 70 : 0;

                Animated.spring(this.pan.y, {
                    toValue: targetPosition,
                    useNativeDriver: true,
                    friction: 8, // Adjust friction for smoothness
                    tension: 100, // Adjust tension for speed
                }).start();
                this.pan.flattenOffset();
                console.log(
                    { ...this.pan.y }, 'AFTER ALL'
                );

                if (targetPosition !== 0) {
                    this.props.dispatch(openDropdown());
                } else {
                    this.props.dispatch(closeDropdown());
                }
            },
            onPanResponderTerminate: (_, gesture) => {
                console.log("PanResponder terminated");
                console.log(
                    { ...this.pan.y }, 'BEFORE'
                );
                this.pan.flattenOffset();
                console.log(
                    this.pan.y, 'AFTER'
                );

                const releasePoint = gesture.moveY;
                this.shouldCollapse = releasePoint > this.screenHeight / 3;

                const targetPosition = this.shouldCollapse ? this.screenHeight - 70 : 0;

                Animated.spring(this.pan.y, {
                    toValue: targetPosition,
                    useNativeDriver: true,
                    friction: 8, // Adjust friction for smoothness
                    tension: 100, // Adjust tension for speed
                }).start();
                this.pan.flattenOffset();
                console.log(
                    { ...this.pan.y }, 'AFTER ALL'
                );

                if (targetPosition !== 0) {
                    this.props.dispatch(openDropdown());
                } else {
                    this.props.dispatch(closeDropdown());
                }
            },
        });

        this.secondPanResponder = PanResponder.create({
            onMoveShouldSetPanResponder: (_, gesture) => {
                // Disable pan handling if touch is slight or near buttons
                return Math.abs(gesture.dx) > 20 || Math.abs(gesture.dy) > 20;
            },
            onStartShouldSetPanResponderCapture: (evt, gesture) => {
                // Block pan for buttons or interactive elements
                return false;
            },
            onPanResponderGrant: () => {
                console.log("SECOND PAN RESPONDER WAS GRANTED ACCESS!!!");
                this.props.dispatch(toggleDropdown());
                this.pan.setValue({ x: 0, y: this.screenHeight - 70 }); // Prevent cumulative gesture errors
            },
            onPanResponderMove: (_, gesture) => {
                this.pan.y.setValue(this.screenHeight - 70 + gesture.dy);
            },
            onPanResponderRelease: (_, gesture) => {
                console.log(
                    { ...this.pan.y }, 'BEFORE'
                );
                this.pan.flattenOffset();
                console.log(
                    { ...this.pan.y }, 'AFTER'
                );
        
                const releasePoint = gesture.moveY;
                this.shouldCollapse = releasePoint < this.screenHeight * 2 / 3;
        
                const targetPosition = this.shouldCollapse ? 0 : this.screenHeight - 70;
        
                Animated.spring(this.pan.y, {
                    toValue: targetPosition,
                    useNativeDriver: true,
                    friction: 8, // Adjust friction for smoothness
                    tension: 100, // Adjust tension for speed
                }).start();
                this.pan.flattenOffset();
                console.log(
                    { ...this.pan.y }, 'AFTER ALL'
                );
        
                if (targetPosition !== 0) {
                    this.props.dispatch(openDropdown());
                } else {
                    this.props.dispatch(closeDropdown());
                }
            },
            onPanResponderTerminate: (_, gesture) => {
                console.log("Second PanResponder terminated");
                console.log(
                    { ...this.pan.y }, 'BEFORE'
                );
                this.pan.flattenOffset();
                console.log(
                    this.pan.y, 'AFTER'
                );
        
                const releasePoint = gesture.moveY;
                this.shouldCollapse = releasePoint < this.screenHeight * 2 / 3;
        
                const targetPosition = this.shouldCollapse ? 0 : this.screenHeight - 70;
        
                Animated.spring(this.pan.y, {
                    toValue: targetPosition,
                    useNativeDriver: true,
                    friction: 8, // Adjust friction for smoothness
                    tension: 100, // Adjust tension for speed
                }).start();
                this.pan.flattenOffset();
                console.log(
                    { ...this.pan.y }, 'AFTER ALL'
                );
        
                if (targetPosition !== 0) {
                    this.props.dispatch(openDropdown());
                } else {
                    this.props.dispatch(closeDropdown());
                }
            },
        });
    }

    componentDidMount() {
        this.props.dispatch(closeDropdown());
        const backHandler = BackHandler.addEventListener(
            "hardwareBackPress",
            () => {
                console.log("Back button pressed, collapsing dropdown");
                Animated.spring(this.pan.y, {
                    toValue: 0,
                    useNativeDriver: true,
                    friction: 8, // Adjust friction for smoothness
                    tension: 100, // Adjust tension for speed
                }).start();
                this.pan.flattenOffset();
                return true; // Prevent default back behavior
            }
        );

        return () => {
            console.log("Removing back handler");
            backHandler.remove(); // Cleanup the event listener on unmount
        };
    }

    doswipedown = () => {
        console.log("Animating to collapse...");
        Animated.spring(this.pan.y, {
            toValue: this.screenHeight - 70,
            useNativeDriver: true,
            friction: 8, // Adjust friction for smoothness
            tension: 100, // Adjust tension for speed
        }).start();
        this.pan.flattenOffset();
        this.props.dispatch(openDropdown());
        console.log(
            { ...this.pan.y }, 'AFTER ALL');
    };

    onPressHandler = (header: ColumnHeader) => {
        console.log(`Header pressed: ${header.value} (link: ${header.link})`);

        this.props.headers.forEach((h: ColumnHeader) => {
            h.isActive = false;
        });

        header.isActive = true;

        this.setState({ activeLink: header.link });
        this.props.navigation.navigate(header.link);
    };

    opendropdown = (page: string, swipedown: boolean) => {
        if (swipedown) this.doswipedown();
        this.setState({ abovePage: page });
    };

    render() {
        const { navigation } = this.props;

        const containerDynamicStyle = {
            height: this.screenHeight + 130,
            top: -50,
            transform: [
                {
                    translateY: this.pan.y.interpolate({
                        inputRange: [0, this.screenHeight - 140], // Adjust based on screen height
                        outputRange: [0, -80], // Adjust minimum and maximum container width
                        extrapolate: "clamp",
                    })
                }],
            borderColor: this.pan.y.interpolate({
                inputRange: [0, 140],
                outputRange: ["#d4f0fe", "rgba(0, 0, 0, 0)"], // From blue to transparent
            }),
        };

        const dynamicIconBox = {
            flex: 1,
            left: this.screenWidth * 0.5 * 0.9,
            position: "absolute" as "absolute",
            opacity: this.pan.y.interpolate({
                inputRange: [0, 20],
                outputRange: [1, 0], // Scale proportionally from 0 to full width
                extrapolate: "clamp",
            }),
        };

        const bottomIconBox = {
            opacity: this.pan.y.interpolate({
                inputRange: [0, this.screenHeight - 140],
                outputRange: [0, 1], // Scale proportionally from 0 to full width
                extrapolate: "clamp",
            }),
            flexDirection: "row" as "row",
            justifyContent: "center" as "center",
            position: "absolute" as "absolute",
            bottom: 5,
            height: 69,
            width: this.screenWidth,
        };

        const dynamicIcon = {
            width: this.screenWidth * 0.25,
            height: this.screenHeight * 0.1,
        };

        const dynamicBackdrop = {
            width: this.screenWidth,
            height: this.screenHeight + 70,
            top: -this.screenHeight,
            transform: [{ translateY: this.pan.y }],
        };

        const dynamictitleBox = {
            transform: [
                {
                    translateX: this.pan.y.interpolate({
                        inputRange: [0, 100], // Adjust based on screen height
                        outputRange: [0, -this.screenWidth], // Adjust minimum and maximum container width
                        extrapolate: "clamp",
                    })
                }],
        };

        const topBoxStyle = {
            top: this.screenHeight + 50,
        };

        const dropdownpageedit = {
            width: this.screenWidth * 0.9,
            marginLeft: this.screenWidth * 0.05,
            marginRight: this.screenWidth * 0.05,
            height: this.screenHeight - 90,
            top: 80,
            transform: [{
                translateY: this.pan.y.interpolate({
                    inputRange: [0, this.screenHeight - 140],
                    outputRange: [0, 130],
                    extrapolate: "clamp",
                }),
            }],
        };

        const renderPage = () => {
            switch (this.state.abovePage) {
                case "Bookings":
                    return (<Animated.View style={[styles.dropdownpage, dropdownpageedit]}><Booking /></Animated.View>);
                case "Bookmarked":
                    return (<Animated.View style={[styles.dropdownpage, dropdownpageedit]}><Saved /></Animated.View>);
                case "Chat":
                    return (<Animated.View style={[styles.dropdownpage, dropdownpageedit]}><Chat /></Animated.View>);
                case "Notification":
                    return (<Animated.View style={[styles.dropdownpage, dropdownpageedit]}><Notification /></Animated.View>);
            }
        };

        return (
            <SafeAreaView>
            <Animated.View style={[styles.backdrop, dynamicBackdrop]}>
                <Animated.View style={[styles.main, containerDynamicStyle]}>
                    {renderPage()}
                    <Animated.ScrollView
                        horizontal
                        scrollEnabled={false}
                        style={[styles.TopBox, topBoxStyle]}
                        {...this.panResponder.panHandlers}
                    >

                        {this.props.headers.length > 1 ? (
                            <Animated.View
                                style={[styles.headerBox, dynamictitleBox]}
                            >
                                {this.props.headers.map((header, index) => (
                                    <TouchableOpacity
                                        key={index}
                                        style={[
                                            styles.headerContainer,
                                            header.isActive && styles.activeButton, // Apply activeButton style if link is active
                                        ]}
                                        onPress={() => this.onPressHandler(header)}
                                    >
                                        <Text style={styles.headerText}>{header.value}</Text>
                                    </TouchableOpacity>
                                ))}
                            </Animated.View>
                        ) : (
                            <View style={{
                                marginTop: 10,
                                marginLeft: 14,
                            }}>
                                <Text style={styles.headerText}>{this.props.headers.map(header => header.value).join(', ')}</Text>
                            </View>
                        )}
                        <Animated.View style={[styles.iconBox, dynamicIconBox]}>
                            <TouchableOpacity onPress={() => this.opendropdown('Notification', true)}><Text>Notification</Text></TouchableOpacity>
                            <TouchableOpacity onPress={() => this.opendropdown('Chat', true)}><Text>Chat</Text></TouchableOpacity>
                        </Animated.View>
                    </Animated.ScrollView>
                </Animated.View>
                <Animated.View style={[styles.bottomIconBox, bottomIconBox]}
                    {...this.secondPanResponder.panHandlers}
                >
                    <TouchableOpacity style={[dynamicIcon, this.state.abovePage === 'Notification' ? styles.activeIcon : null]} onPress={() => this.opendropdown('Notification', false)}><Text>Notification</Text></TouchableOpacity>
                    <TouchableOpacity style={[dynamicIcon, this.state.abovePage === 'Chat' ? styles.activeIcon : null]} onPress={() => this.opendropdown('Chat', false)}><Text>Chat</Text></TouchableOpacity>
                    <TouchableOpacity style={[dynamicIcon, this.state.abovePage === 'Bookmarked' ? styles.activeIcon : null]} onPress={() => this.opendropdown('Bookmarked', false)}><Animated.Text>Bookmark</Animated.Text></TouchableOpacity>
                    <TouchableOpacity style={[dynamicIcon, this.state.abovePage === 'Bookings' ? styles.activeIcon : null]} onPress={() => this.opendropdown('Bookings', false)}><Animated.Text>Bookings</Animated.Text></TouchableOpacity>
                </Animated.View>
            </Animated.View >
            </SafeAreaView>
        );
    }
}

// Map state from Redux store to component props
interface StoreState {
    navigation: {
        dropdownOpened: boolean;
        dropdownStatic: boolean;
    };
}

const mapStateToProps = (store: StoreState) => ({
    dropdownOpened: store.navigation.dropdownOpened,
    dropdownStatic: store.navigation.dropdownStatic,
});

export default connect(mapStateToProps)(Dropdown);