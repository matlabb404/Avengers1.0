import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    mainpost: {
        flex:1,
        width: '100%',
        backgroundColor: theme.colors.primary,
    },
    maincard: {
        flex:1,
        width: '100%',
    },
    namecontainer: {
        width: '96%',
        marginRight: '2%',
        marginLeft: '2%',
        height: theme.sizes.xxxlarge,
    },
    vendorname: {
        color: theme.colors.font,
        fontSize: theme.sizes.xxlarge,
        fontWeight: 800,
    },
    descriptionbox: {
        marginLeft: '2%',
        marginRight: '2%',
        paddingTop: 3,
        width: '96%',
    },
    mediaconatinaer: {
        zIndex: 66,
        width: '96%',
        marginRight: '2%',
        marginLeft: '2%',
        marginBottom:0,
        marginTop:0,
    },
    mediaImage: {
        width: '100%',
        // marginRight: 0.5,
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
        borderBottomWidth: 2,
        // marginTop: 2,
        // paddingBottom: 4,
        borderColor: theme.colors.secondary,
    },
    iconcontainer: {
        flex: 1,
        width: '100%',
        height: 50,
        justifyContent: 'center',
    },
});

export default styles;