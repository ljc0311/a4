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
import{dcLocalStorage as o}from"../../../common/local-storage.js";import{events as t}from"../../../common/analytics.js";import{LOCAL_FILE_PERMISSION_URL as e,ONE_DAY_IN_MS as r}from"../../../common/constant.js";import{floodgate as n}from"../../../sw_modules/floodgate.js";import{util as i}from"../../js/content-util.js";import{loggingApi as l}from"../../../common/loggingApi.js";const a="Error in Local File Prompt";async function s(){try{i.translateElements(".translate");const t=document.getElementById("local-file-animated-fte");t?t.style.backgroundImage="url(../../images/LocalizedFte/en_US/fte_old.svg)":l.error({message:a+"initialize: FTE element not found"});document.getElementById("localFilePromptContinueButton").addEventListener("click",c),await o.init()}catch(o){l.error({message:a,error:`initialize: Error in initialization: ${o}`})}}async function c(){try{i.sendAnalytics(t.LOCAL_FTE_GO_TO_SETTINGS_CLICKED);!function(t){try{let e=o.getItem("localFileConfig");e||(e={promptCount:1}),e.eligibleDate=function(o){const t=Number(o?.settingsCoolDown);Number.isNaN(t)&&l.error({message:a,error:`_getLocalFilePromptCooldown: cooldownConfig.settingsCoolDown must be a valid number: ${o?.settingsCoolDown}`});return new Date(Date.now()+t*r).toISOString()}(t),o.setItem("localFileConfig",e)}catch(o){l.error({message:a,error:`_updateLocalFilePromptCooldown: Error updating local file prompt cooldown: ${o}`})}}(await function(){let o;try{o=n.getFeatureMeta("dc-cv-local-file-permission-prompt"),o=JSON.parse(o)}catch(t){l.error({message:a,error:`_fetchLocalFilePromptCooldownConfig: Error fetching local file prompt cooldown config: ${t}`}),o={promptLimit:5,ignoreCoolDown:7,settingsCoolDown:7,dismissCoolDown:7}}return o}());const s=o.getItem("localFteWindow");if(s){const{id:t,height:r,width:n,left:i,top:c}=s;chrome.windows.create({height:r,width:n,left:i,top:c,focused:!0,type:"popup",url:e},(e=>{chrome.runtime.lastError?l.error({message:a,error:"handleSettingsButtonCLick: Error creating window"}):(o.setItem("settingsWindow",{id:e.tabs[0].id}),chrome.windows.remove(t))}))}else l.error({message:a,error:"handleSettingsButtonCLick: Window configuration not found in storage"})}catch(o){l.error({message:a,error:`handleSettingsButtonCLick: Error in button click handler: ${o}`})}}"loading"===document.readyState?document.addEventListener("DOMContentLoaded",s):s();