/*
 Navicat Premium Dump SQL

 Source Server         : mariaDB10
 Source Server Type    : MariaDB
 Source Server Version : 101111 (10.11.11-MariaDB)
 Source Host           : 192.168.31.146:3307
 Source Schema         : cookbook

 Target Server Type    : MariaDB
 Target Server Version : 101111 (10.11.11-MariaDB)
 File Encoding         : 65001

 Date: 03/08/2026 12:00:55
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for cook_activate
-- ----------------------------
DROP TABLE IF EXISTS `cook_activate`;
CREATE TABLE `cook_activate`  (
  `reg_ID` int(11) NOT NULL AUTO_INCREMENT,
  `reg_InviteCode` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `reg_Level` int(11) NOT NULL DEFAULT 5,
  `reg_AuthorID` int(11) NOT NULL DEFAULT 0,
  `reg_IsUsed` tinyint(1) NOT NULL DEFAULT 0,
  `reg_uptime` int(11) NOT NULL DEFAULT 0,
  `reg_Intro` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`reg_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_category
-- ----------------------------
DROP TABLE IF EXISTS `cook_category`;
CREATE TABLE `cook_category`  (
  `cate_ID` int(11) NOT NULL AUTO_INCREMENT,
  `cate_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cate_Order` int(11) NOT NULL DEFAULT 0,
  `cate_Type` int(11) NOT NULL DEFAULT 0,
  `cate_Count` int(11) NOT NULL DEFAULT 0,
  `cate_Alias` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cate_Group` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cate_Intro` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `cate_RootID` int(11) NOT NULL DEFAULT 0,
  `cate_ParentID` int(11) NOT NULL DEFAULT 0,
  `cate_CreateTime` int(11) NOT NULL DEFAULT 0,
  `cate_PostTime` int(11) NOT NULL DEFAULT 0,
  `cate_UpdateTime` int(11) NOT NULL DEFAULT 0,
  `cate_Template` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cate_LogTemplate` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cate_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`cate_ID`) USING BTREE,
  INDEX `cook_cate_Order`(`cate_Order`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 6 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_comment
-- ----------------------------
DROP TABLE IF EXISTS `cook_comment`;
CREATE TABLE `cook_comment`  (
  `comm_ID` int(11) NOT NULL AUTO_INCREMENT,
  `comm_LogID` int(11) NOT NULL DEFAULT 0,
  `comm_IsChecking` tinyint(4) NOT NULL DEFAULT 0,
  `comm_RootID` int(11) NOT NULL DEFAULT 0,
  `comm_ParentID` int(11) NOT NULL DEFAULT 0,
  `comm_AuthorID` int(11) NOT NULL DEFAULT 0,
  `comm_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `comm_Email` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `comm_HomePage` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `comm_Content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `comm_PostTime` int(11) NOT NULL DEFAULT 0,
  `comm_IP` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `comm_Agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `comm_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`comm_ID`) USING BTREE,
  INDEX `cook_comm_LRI`(`comm_LogID`, `comm_RootID`, `comm_IsChecking`) USING BTREE,
  INDEX `cook_comm_IsChecking`(`comm_IsChecking`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_config
-- ----------------------------
DROP TABLE IF EXISTS `cook_config`;
CREATE TABLE `cook_config`  (
  `conf_ID` int(11) NOT NULL AUTO_INCREMENT,
  `conf_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `conf_Key` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `conf_Value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`conf_ID`) USING BTREE,
  INDEX `cook_conf_Name`(`conf_Name`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 558 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_consume
-- ----------------------------
DROP TABLE IF EXISTS `cook_consume`;
CREATE TABLE `cook_consume`  (
  `cs_id` int(11) NOT NULL AUTO_INCREMENT,
  `cs_uid` int(11) NOT NULL DEFAULT 0,
  `cs_pid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cs_title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `cs_time` int(11) NOT NULL DEFAULT 0,
  `cs_money` int(11) NOT NULL DEFAULT 0,
  `cs_type` int(11) NOT NULL DEFAULT 0,
  `cs_class` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`cs_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 8 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_daybuy
-- ----------------------------
DROP TABLE IF EXISTS `cook_daybuy`;
CREATE TABLE `cook_daybuy`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `oid` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0',
  `pid` int(11) NOT NULL DEFAULT 0,
  `uid` int(11) NOT NULL DEFAULT 0,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `state` int(11) NOT NULL DEFAULT 0,
  `addtime` int(11) NOT NULL DEFAULT 0,
  `price` int(11) NOT NULL DEFAULT 0,
  `express` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `ip` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_daybuyview
-- ----------------------------
DROP TABLE IF EXISTS `cook_daybuyview`;
CREATE TABLE `cook_daybuyview`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pid` int(11) NOT NULL DEFAULT 0,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `price` int(11) NOT NULL DEFAULT 0,
  `type` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_daycode
-- ----------------------------
DROP TABLE IF EXISTS `cook_daycode`;
CREATE TABLE `cook_daycode`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uid` int(11) NOT NULL DEFAULT 0,
  `count` int(11) NOT NULL DEFAULT 0,
  `sendtime` int(11) NOT NULL DEFAULT 0,
  `expiretime` int(11) NOT NULL DEFAULT 0,
  `ip` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `account` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `type` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_daylog
-- ----------------------------
DROP TABLE IF EXISTS `cook_daylog`;
CREATE TABLE `cook_daylog`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uid` int(11) NOT NULL DEFAULT 0,
  `pid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `time` int(11) NOT NULL DEFAULT 0,
  `money` int(11) NOT NULL DEFAULT 0,
  `endmoney` int(11) NOT NULL DEFAULT 0,
  `type` int(11) NOT NULL DEFAULT 0,
  `class` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_daypay
-- ----------------------------
DROP TABLE IF EXISTS `cook_daypay`;
CREATE TABLE `cook_daypay`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `alipay_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tradeno` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `paytradeno` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `user_id` int(11) NOT NULL DEFAULT 0,
  `money` int(11) NOT NULL DEFAULT 0,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `geteway` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `sign` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `state` int(11) NOT NULL DEFAULT 0,
  `addtime` int(11) NOT NULL DEFAULT 0,
  `paytime` int(11) NOT NULL DEFAULT 0,
  `updatetime` int(11) NOT NULL DEFAULT 0,
  `ip` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `type` int(11) NOT NULL DEFAULT 0,
  `more` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_dayprepaid
-- ----------------------------
DROP TABLE IF EXISTS `cook_dayprepaid`;
CREATE TABLE `cook_dayprepaid`  (
  `tc_ID` int(11) NOT NULL AUTO_INCREMENT,
  `tc_InviteCode` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tc_Price` int(11) NOT NULL DEFAULT 0,
  `tc_AuthorID` int(11) NOT NULL DEFAULT 0,
  `tc_IsUsed` tinyint(1) NOT NULL DEFAULT 0,
  `tc_uptime` int(11) NOT NULL DEFAULT 0,
  `tc_Intro` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`tc_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_daysign
-- ----------------------------
DROP TABLE IF EXISTS `cook_daysign`;
CREATE TABLE `cook_daysign`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uid` int(11) NOT NULL DEFAULT 0,
  `count` int(11) NOT NULL DEFAULT 0,
  `sendtime` int(11) NOT NULL DEFAULT 0,
  `expiretime` int(11) NOT NULL DEFAULT 0,
  `ip` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `account` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `type` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_dayuser
-- ----------------------------
DROP TABLE IF EXISTS `cook_dayuser`;
CREATE TABLE `cook_dayuser`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uid` int(11) NOT NULL DEFAULT 0,
  `oid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `Price` int(11) NOT NULL DEFAULT 0,
  `Vipendtime` int(11) NOT NULL DEFAULT 0,
  `isidcard` int(11) NOT NULL DEFAULT 0,
  `idcard` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `rootid` int(11) NOT NULL DEFAULT 0,
  `tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `score` int(11) NOT NULL DEFAULT 0,
  `coin` int(11) NOT NULL DEFAULT 0,
  `balance` int(11) NOT NULL DEFAULT 0,
  `createtime` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_favorite
-- ----------------------------
DROP TABLE IF EXISTS `cook_favorite`;
CREATE TABLE `cook_favorite`  (
  `fa_id` int(11) NOT NULL AUTO_INCREMENT,
  `fa_uid` int(11) NOT NULL DEFAULT 0,
  `fa_pid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `fa_time` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`fa_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_member
-- ----------------------------
DROP TABLE IF EXISTS `cook_member`;
CREATE TABLE `cook_member`  (
  `mem_ID` int(11) NOT NULL AUTO_INCREMENT,
  `mem_Guid` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_Level` tinyint(4) NOT NULL DEFAULT 0,
  `mem_Status` tinyint(4) NOT NULL DEFAULT 0,
  `mem_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_Password` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_Email` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_HomePage` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_IP` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_CreateTime` int(11) NOT NULL DEFAULT 0,
  `mem_PostTime` int(11) NOT NULL DEFAULT 0,
  `mem_UpdateTime` int(11) NOT NULL DEFAULT 0,
  `mem_Alias` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_Intro` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `mem_Articles` int(11) NOT NULL DEFAULT 0,
  `mem_Pages` int(11) NOT NULL DEFAULT 0,
  `mem_Comments` int(11) NOT NULL DEFAULT 0,
  `mem_Uploads` int(11) NOT NULL DEFAULT 0,
  `mem_Template` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mem_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`mem_ID`) USING BTREE,
  INDEX `cook_mem_Name`(`mem_Name`) USING BTREE,
  INDEX `cook_mem_Alias`(`mem_Alias`) USING BTREE,
  INDEX `cook_mem_Level`(`mem_Level`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_module
-- ----------------------------
DROP TABLE IF EXISTS `cook_module`;
CREATE TABLE `cook_module`  (
  `mod_ID` int(11) NOT NULL AUTO_INCREMENT,
  `mod_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mod_FileName` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mod_Content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `mod_SidebarID` int(11) NOT NULL DEFAULT 0,
  `mod_HtmlID` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mod_Type` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mod_MaxLi` int(11) NOT NULL DEFAULT 0,
  `mod_Source` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `mod_IsHideTitle` tinyint(4) NOT NULL DEFAULT 0,
  `mod_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`mod_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 87 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_post
-- ----------------------------
DROP TABLE IF EXISTS `cook_post`;
CREATE TABLE `cook_post`  (
  `log_ID` int(11) NOT NULL AUTO_INCREMENT,
  `log_CateID` int(11) NOT NULL DEFAULT 0,
  `log_AuthorID` int(11) NOT NULL DEFAULT 0,
  `log_Tag` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `log_Status` tinyint(4) NOT NULL DEFAULT 0,
  `log_Type` int(11) NOT NULL DEFAULT 0,
  `log_Alias` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `log_IsTop` tinyint(4) NOT NULL DEFAULT 0,
  `log_IsLock` tinyint(4) NOT NULL DEFAULT 0,
  `log_Title` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `log_Intro` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `log_Content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `log_CreateTime` int(11) NOT NULL DEFAULT 0,
  `log_PostTime` int(11) NOT NULL DEFAULT 0,
  `log_UpdateTime` int(11) NOT NULL DEFAULT 0,
  `log_CommNums` int(11) NOT NULL DEFAULT 0,
  `log_ViewNums` int(11) NOT NULL DEFAULT 0,
  `log_Template` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `log_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`log_ID`) USING BTREE,
  INDEX `cook_log_TPISC`(`log_Type`, `log_PostTime`, `log_IsTop`, `log_Status`, `log_CateID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_prepaid
-- ----------------------------
DROP TABLE IF EXISTS `cook_prepaid`;
CREATE TABLE `cook_prepaid`  (
  `tc_ID` int(11) NOT NULL AUTO_INCREMENT,
  `tc_InviteCode` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tc_Price` int(11) NOT NULL DEFAULT 0,
  `tc_AuthorID` int(11) NOT NULL DEFAULT 0,
  `tc_IsUsed` tinyint(1) NOT NULL DEFAULT 0,
  `tc_uptime` int(11) NOT NULL DEFAULT 0,
  `tc_Intro` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`tc_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_tag
-- ----------------------------
DROP TABLE IF EXISTS `cook_tag`;
CREATE TABLE `cook_tag`  (
  `tag_ID` int(11) NOT NULL AUTO_INCREMENT,
  `tag_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tag_Order` int(11) NOT NULL DEFAULT 0,
  `tag_Type` int(11) NOT NULL DEFAULT 0,
  `tag_Count` int(11) NOT NULL DEFAULT 0,
  `tag_Alias` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tag_Group` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tag_Intro` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tag_CreateTime` int(11) NOT NULL DEFAULT 0,
  `tag_PostTime` int(11) NOT NULL DEFAULT 0,
  `tag_UpdateTime` int(11) NOT NULL DEFAULT 0,
  `tag_Template` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tag_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`tag_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_upload
-- ----------------------------
DROP TABLE IF EXISTS `cook_upload`;
CREATE TABLE `cook_upload`  (
  `ul_ID` int(11) NOT NULL AUTO_INCREMENT,
  `ul_AuthorID` int(11) NOT NULL DEFAULT 0,
  `ul_Size` int(11) NOT NULL DEFAULT 0,
  `ul_Name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `ul_SourceName` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `ul_MimeType` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `ul_PostTime` int(11) NOT NULL DEFAULT 0,
  `ul_DownNums` int(11) NOT NULL DEFAULT 0,
  `ul_LogID` int(11) NOT NULL DEFAULT 0,
  `ul_Intro` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `ul_Meta` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`ul_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_ytbuyview
-- ----------------------------
DROP TABLE IF EXISTS `cook_ytbuyview`;
CREATE TABLE `cook_ytbuyview`  (
  `buy_id` int(11) NOT NULL AUTO_INCREMENT,
  `buy_content` int(11) NOT NULL DEFAULT 0,
  `buy_Price` int(11) NOT NULL DEFAULT 0,
  `buy_type` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`buy_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Fixed;

-- ----------------------------
-- Table structure for cook_ytuser
-- ----------------------------
DROP TABLE IF EXISTS `cook_ytuser`;
CREATE TABLE `cook_ytuser`  (
  `tc_id` int(11) NOT NULL AUTO_INCREMENT,
  `tc_uid` int(11) NOT NULL DEFAULT 0,
  `tc_oid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tc_Price` int(11) NOT NULL DEFAULT 0,
  `tc_Vipendtime` int(11) NOT NULL DEFAULT 0,
  `tc_isidcard` int(11) NOT NULL DEFAULT 0,
  `tc_idcard` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tc_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `tc_rootid` int(11) NOT NULL DEFAULT 0,
  `tc_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`tc_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_ytuser_buy
-- ----------------------------
DROP TABLE IF EXISTS `cook_ytuser_buy`;
CREATE TABLE `cook_ytuser_buy`  (
  `buy_ID` int(11) NOT NULL AUTO_INCREMENT,
  `buy_OrderID` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0',
  `buy_LogID` int(11) NOT NULL DEFAULT 0,
  `buy_AuthorID` int(11) NOT NULL DEFAULT 0,
  `buy_Title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `buy_State` int(11) NOT NULL DEFAULT 0,
  `buy_PostTime` int(11) NOT NULL DEFAULT 0,
  `buy_Pay` int(11) NOT NULL DEFAULT 0,
  `buy_Express` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `buy_IP` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`buy_ID`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cook_ytverification
-- ----------------------------
DROP TABLE IF EXISTS `cook_ytverification`;
CREATE TABLE `cook_ytverification`  (
  `vf_id` int(11) NOT NULL AUTO_INCREMENT,
  `vf_uid` int(11) NOT NULL DEFAULT 0,
  `vf_count` int(11) NOT NULL DEFAULT 0,
  `vf_sendtime` int(11) NOT NULL DEFAULT 0,
  `vf_expiretime` int(11) NOT NULL DEFAULT 0,
  `vf_ip` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `vf_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `vf_account` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `vf_type` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`vf_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_categories
-- ----------------------------
DROP TABLE IF EXISTS `user_categories`;
CREATE TABLE `user_categories`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `parent_id` int(10) UNSIGNED NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  `updated_at` datetime NULL DEFAULT current_timestamp() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `parent_id`(`parent_id` ASC) USING BTREE,
  CONSTRAINT `fk_user_categories_parent` FOREIGN KEY (`parent_id`) REFERENCES `user_categories` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_daily_recipes
-- ----------------------------
DROP TABLE IF EXISTS `user_daily_recipes`;
CREATE TABLE `user_daily_recipes`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int(10) UNSIGNED NOT NULL COMMENT '用户ID',
  `recipe_id` int(10) UNSIGNED NOT NULL COMMENT '菜谱ID',
  `target_date` date NOT NULL COMMENT '指定日期',
  `created_at` datetime NULL DEFAULT current_timestamp(),
  `updated_at` datetime NULL DEFAULT current_timestamp() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_user_recipe_date`(`user_id` ASC, `recipe_id` ASC, `target_date` ASC) USING BTREE,
  INDEX `idx_user_date`(`user_id` ASC, `target_date` ASC) USING BTREE,
  INDEX `idx_recipe_id`(`recipe_id` ASC) USING BTREE,
  INDEX `idx_target_date`(`target_date` ASC) USING BTREE,
  CONSTRAINT `fk_daily_recipe_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_daily_recipe_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 20 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_favorites
-- ----------------------------
DROP TABLE IF EXISTS `user_favorites`;
CREATE TABLE `user_favorites`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int(10) UNSIGNED NOT NULL,
  `recipe_id` int(10) UNSIGNED NOT NULL,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_favorite`(`user_id` ASC, `recipe_id` ASC) USING BTREE,
  INDEX `recipe_id`(`recipe_id` ASC) USING BTREE,
  CONSTRAINT `fk_user_favorites_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_user_favorites_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_history
-- ----------------------------
DROP TABLE IF EXISTS `user_history`;
CREATE TABLE `user_history`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int(10) UNSIGNED NOT NULL,
  `recipe_id` int(10) UNSIGNED NOT NULL,
  `viewed_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `user_id`(`user_id` ASC, `recipe_id` ASC) USING BTREE,
  INDEX `recipe_id`(`recipe_id` ASC) USING BTREE,
  INDEX `idx_user_viewed`(`user_id` ASC, `viewed_at` ASC) USING BTREE,
  CONSTRAINT `fk_user_history_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_user_history_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 341 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_ing_categories
-- ----------------------------
DROP TABLE IF EXISTS `user_ing_categories`;
CREATE TABLE `user_ing_categories`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 12 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_ingredients
-- ----------------------------
DROP TABLE IF EXISTS `user_ingredients`;
CREATE TABLE `user_ingredients`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `pinyin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` int(10) UNSIGNED NULL DEFAULT 1,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `category_id`(`category_id` ASC) USING BTREE,
  INDEX `name_2`(`name` ASC) USING BTREE,
  INDEX `pinyin`(`pinyin` ASC) USING BTREE,
  CONSTRAINT `fk_user_ingredients_category` FOREIGN KEY (`category_id`) REFERENCES `user_ing_categories` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 35 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_recipe_categories
-- ----------------------------
DROP TABLE IF EXISTS `user_recipe_categories`;
CREATE TABLE `user_recipe_categories`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `recipe_id` int(10) UNSIGNED NOT NULL,
  `category_id` int(10) UNSIGNED NOT NULL,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_mapping`(`recipe_id` ASC, `category_id` ASC) USING BTREE,
  INDEX `recipe_id`(`recipe_id` ASC) USING BTREE,
  INDEX `category_id`(`category_id` ASC) USING BTREE,
  CONSTRAINT `fk_recipe_categories_category` FOREIGN KEY (`category_id`) REFERENCES `user_categories` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_recipe_categories_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 55 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_recipe_ingredients
-- ----------------------------
DROP TABLE IF EXISTS `user_recipe_ingredients`;
CREATE TABLE `user_recipe_ingredients`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `recipe_id` int(10) UNSIGNED NOT NULL,
  `ingredient_id` int(10) UNSIGNED NOT NULL,
  `quantity` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_recipe_ingredient`(`recipe_id` ASC, `ingredient_id` ASC) USING BTREE,
  INDEX `ingredient_id`(`ingredient_id` ASC) USING BTREE,
  CONSTRAINT `fk_recipe_ingredients_ingredient` FOREIGN KEY (`ingredient_id`) REFERENCES `user_ingredients` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_recipe_ingredients_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 162 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_recipe_seasonings
-- ----------------------------
DROP TABLE IF EXISTS `user_recipe_seasonings`;
CREATE TABLE `user_recipe_seasonings`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `recipe_id` int(10) UNSIGNED NOT NULL,
  `seasoning_id` int(10) UNSIGNED NOT NULL,
  `quantity` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_recipe_seasoning`(`recipe_id` ASC, `seasoning_id` ASC) USING BTREE,
  INDEX `seasoning_id`(`seasoning_id` ASC) USING BTREE,
  INDEX `recipe_id`(`recipe_id` ASC) USING BTREE,
  CONSTRAINT `fk_recipe_seasonings_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_recipe_seasonings_seasoning` FOREIGN KEY (`seasoning_id`) REFERENCES `user_seasonings` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 275 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_recipes
-- ----------------------------
DROP TABLE IF EXISTS `user_recipes`;
CREATE TABLE `user_recipes`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int(10) UNSIGNED NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `pinyin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cover` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `cook_time` int(11) NULL DEFAULT NULL COMMENT '分钟',
  `view_count` int(10) UNSIGNED NULL DEFAULT 0,
  `favorite_count` int(10) UNSIGNED NULL DEFAULT 0,
  `is_deleted` tinyint(1) GENERATED ALWAYS AS (`deleted_at` is not null) PERSISTENT,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  `updated_at` datetime NULL DEFAULT current_timestamp() ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_user_title_not_deleted`(`user_id` ASC, `title` ASC) USING BTREE,
  INDEX `idx_user_not_deleted`(`user_id` ASC, `is_deleted` ASC, `created_at` ASC) USING BTREE,
  INDEX `idx_created`(`created_at` ASC) USING BTREE,
  INDEX `idx_not_deleted_created`(`is_deleted` ASC, `created_at` ASC) USING BTREE,
  INDEX `idx_pinyin`(`pinyin` ASC) USING BTREE,
  INDEX `idx_title`(`title` ASC) USING BTREE,
  FULLTEXT INDEX `ft_title_description`(`title`, `description`),
  CONSTRAINT `fk_user_recipes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_seasoning_categories
-- ----------------------------
DROP TABLE IF EXISTS `user_seasoning_categories`;
CREATE TABLE `user_seasoning_categories`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_seasonings
-- ----------------------------
DROP TABLE IF EXISTS `user_seasonings`;
CREATE TABLE `user_seasonings`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `pinyin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` int(10) UNSIGNED NULL DEFAULT 1,
  `created_at` datetime NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `category_id`(`category_id` ASC) USING BTREE,
  INDEX `name_2`(`name` ASC) USING BTREE,
  INDEX `pinyin`(`pinyin` ASC) USING BTREE,
  CONSTRAINT `fk_user_seasonings_category` FOREIGN KEY (`category_id`) REFERENCES `user_seasoning_categories` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 26 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_steps
-- ----------------------------
DROP TABLE IF EXISTS `user_steps`;
CREATE TABLE `user_steps`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `recipe_id` int(10) UNSIGNED NOT NULL,
  `step_order` int(11) NOT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_step_order`(`recipe_id` ASC, `step_order` ASC) USING BTREE,
  INDEX `recipe_id`(`recipe_id` ASC) USING BTREE,
  CONSTRAINT `fk_user_steps_recipe` FOREIGN KEY (`recipe_id`) REFERENCES `user_recipes` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 218 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `username`(`username` ASC) USING BTREE,
  UNIQUE INDEX `email`(`email` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Event structure for ev_cleanup_deleted_recipes
-- ----------------------------
DROP EVENT IF EXISTS `ev_cleanup_deleted_recipes`;
delimiter ;;
CREATE EVENT `ev_cleanup_deleted_recipes`
ON SCHEDULE
EVERY '1' DAY STARTS '2026-03-09 20:00:24'
DO DELETE FROM user_recipes
WHERE deleted_at IS NOT NULL
  AND deleted_at < NOW() - INTERVAL 30 DAY
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table user_categories
-- ----------------------------
DROP TRIGGER IF EXISTS `prevent_update_default_category`;
delimiter ;;
CREATE TRIGGER `prevent_update_default_category` BEFORE UPDATE ON `user_categories` FOR EACH ROW BEGIN
    IF OLD.id = 1 AND NEW.id <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '默认分类ID不可修改';
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table user_categories
-- ----------------------------
DROP TRIGGER IF EXISTS `prevent_delete_default_category`;
delimiter ;;
CREATE TRIGGER `prevent_delete_default_category` BEFORE DELETE ON `user_categories` FOR EACH ROW BEGIN
    IF OLD.id = 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '默认分类不可删除';
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table user_ing_categories
-- ----------------------------
DROP TRIGGER IF EXISTS `prevent_update_default_ing_category`;
delimiter ;;
CREATE TRIGGER `prevent_update_default_ing_category` BEFORE UPDATE ON `user_ing_categories` FOR EACH ROW BEGIN
    IF OLD.id = 1 AND NEW.id <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '默认食材分类ID不可修改';
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table user_ing_categories
-- ----------------------------
DROP TRIGGER IF EXISTS `prevent_delete_default_ing_category`;
delimiter ;;
CREATE TRIGGER `prevent_delete_default_ing_category` BEFORE DELETE ON `user_ing_categories` FOR EACH ROW BEGIN
    IF OLD.id = 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '默认食材分类不可删除';
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table user_seasoning_categories
-- ----------------------------
DROP TRIGGER IF EXISTS `prevent_update_default_seasoning_category`;
delimiter ;;
CREATE TRIGGER `prevent_update_default_seasoning_category` BEFORE UPDATE ON `user_seasoning_categories` FOR EACH ROW BEGIN
    IF OLD.id = 1 AND NEW.id <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '默认调料分类ID不可修改';
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table user_seasoning_categories
-- ----------------------------
DROP TRIGGER IF EXISTS `prevent_delete_default_seasoning_category`;
delimiter ;;
CREATE TRIGGER `prevent_delete_default_seasoning_category` BEFORE DELETE ON `user_seasoning_categories` FOR EACH ROW BEGIN
    IF OLD.id = 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '默认调料分类不可删除';
    END IF;
END
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
