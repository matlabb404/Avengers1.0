import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    mainpost: {
        // borderWidth: 1, // Add border
        // borderColor: 'yellow', // Make it visible]
        position: 'absolute',
        backgroundColor: theme.colors.primary,
    },
    maincard: {
        width: '100%',
    },
    namecontainer: {
        // borderWidth: 1, // Add border
        // borderColor: 'yellow', // Make it visible]
        width: '96%',
        marginRight: '2%',
        marginLeft: '2%',
        height: theme.sizes.xxxlarge,
    },
    vendorname: {
        color: theme.colors.font,
        fontSize: theme.sizes.xlarge,
        fontWeight: 800,
    },
    descriptionbox: {
        paddingLeft: '2%',
        paddingRight: '1%',
        paddingTop: 3,
        width: '96%',
        alignItems: 'center',
        // borderWidth: 1, // Add border
        // borderColor: 'yellow', // Make it visible]
    },
    mediaconatinaer: {
        // borderWidth: 1, // Add border
        // borderColor: 'yellow', // Make it visible]
        marginBottom:0,
        marginTop:0,
    },
    mediaImage: {
        // marginRight: 0.5,
        // borderWidth: 1, // Add border
        // borderColor: 'yellow', // Make it visible]
        // marginLeft: 0.5,
        // marginTop: 5,
        // marginBottom: 5,
        // borderRadius: 5,
    },
    reviews: {
        width: '96%',
        marginRight: '2%',
        marginLeft: '2%',
        // height: 22,
        // paddingLeft: 6,
        // paddingRight: 7,
        // borderWidth: 1, // Add border
        // borderBottomWidth: 2,
        // marginTop: 2,
        // paddingBottom: 4,
        borderColor: theme.colors.secondary,
    },
    iconcontainer: {
        marginRight: '2%',
        marginLeft: '2%',
        width: '96%',
        borderWidth: 1, // Add border
        borderLeftWidth: 0,
        borderRightWidth: 0,
        borderColor: theme.colors.inactive, // Make it visible]
        height: 50,
        justifyContent: 'center',
    },
});

export default styles;