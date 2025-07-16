/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
import{util as e}from"../js/content-util.js";import{events as t}from"../../common/analytics.js";import{dcSessionStorage as n}from"../../common/local-storage.js";import{OptionPageActions as a,OptionsPageSource as s}from"../../common/constant.js";await n.init(),chrome.runtime.sendMessage({main_op:"getFloodgateFlag",flag:"dc-cv-genai-markers-impression-analytics",cachePurge:"NO_CALL"},(n=>{n&&e.sendAnalytics(t.AI_ASSISTANT_SUMMARY_PILL_SHOWN)})),window.addEventListener("message",(e=>{"exit"===e.data.action&&document.querySelector(".popup").classList.add("exit")})),$(document).ready((()=>{e.translateElements(".translate");const o=e.getSearchParamFromURL("pdfMarkerLink",window.location.href);!function(e){const t=document.getElementById("assitantPopup");"dark"===e?t.setAttribute("data-theme","dark"):t.setAttribute("data-theme","light")}(e.getSearchParamFromURL("theme",window.location.href)),async function(e){"false"===(await chrome.storage.local.get("pdfViewer"))?.pdfViewer&&chrome.runtime.sendMessage({main_op:"hideAIMarkerPopup",href:e})}(o),$("#getSummary").click((()=>{if(e.sendAnalytics(t.AI_ASSISTANT_SUMMARY_CTA_CLICKED),n.setWithTTL("pdfMarkerAction",!0,5e3),o){const e=chrome.runtime.getURL("viewer.html")+"?pdfurl="+o;window.open(e,"_blank")}}));let i=!1;$("#menu").click((()=>{i=!i,i?($("#menu").attr("src","../images/SDC_Close_18_N.svg"),$("#menu").addClass("active"),$(".menuList").show(),e.sendAnalytics(t.AI_ASSISTANT_MENU_DROPDOWN_SHOWN)):($("#menu").attr("src","../images/SDC_ShowMenu_18_N.svg"),$("#menu").removeClass("active"),$(".menuList").hide()),chrome.runtime.sendMessage({main_op:"updateIframeHeight",href:o,menuOpen:i})})),$("#menuItem1").click((()=>{e.sendAnalytics(t.AI_ASSISTANT_MENU_HIDE_FOR_SESSION_CLICKED),chrome.runtime.sendMessage({main_op:"hideAIMarkerPopup",href:o})})),$("#menuItem2").click((()=>{e.sendAnalytics(t.AI_ASSISTANT_MENU_SETTINGS_CLICKED),chrome.runtime.openOptionsPage((e=>{setTimeout((()=>{chrome.runtime.sendMessage({requestType:a.OPTIONS_HIGHLIGHT_SECTION,sectionClassNames:["ai-contextual-menu-section","ai-contextual-menu-toggle"]}),chrome.runtime.sendMessage({requestType:a.OPTIONS_SET_OPTIONS_PAGE_SOURCE,optionsPageSource:s.AI_CONTEXTUAL_MENU})}),100)}))}))}));