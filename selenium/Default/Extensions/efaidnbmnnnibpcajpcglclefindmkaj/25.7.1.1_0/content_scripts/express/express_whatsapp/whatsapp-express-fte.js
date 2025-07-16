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
class WhatsappExpressFte{id="WhatsappExpressFte";timeout=3e3;maxFteCount=3;fteGapBetweenIterations=6048e5;whatsappExpressStateKey="whatsappExpressState";whatsappExpressInitialState={previewTouchpointUsed:!1,hoverTouchpointUsed:!1,fte:{shown:0,lastShown:null}};constructor(){this.initPromise=this.init()}isEligible=async()=>{if(await this.initPromise,!this.config?.enableWhatsappPreviewExpressFte)return!1;let t=await chrome.storage.local.get(this.whatsappExpressStateKey);if(t?.whatsappExpressState?t=t.whatsappExpressState:(t=this.whatsappExpressInitialState,chrome.storage.local.set({[this.whatsappExpressStateKey]:t})),t.previewTouchpointUsed)return!1;if(t.fte?.shown>=this.maxFteCount)return!1;if(t.fte?.lastShown&&t.fte?.lastShown+this.fteGapBetweenIterations>Date.now())return!1;return!!await this.getCtaElement()};render=async()=>{const t=await this.getCtaElement();t&&(this.expressContextualFTE=new this.expressContextualFteClass("whatsappPreview",t,{fteTitle:this.config.fteStrings.title,fteDescription:this.config.fteStrings.description,fteCtaLabel:this.config.fteStrings.ctaLabel},this.updateWhatsappExpressState),await this.expressContextualFTE.render())};getCtaElement=async()=>{for(let t=0;t<10;t++){const t=document.getElementById("whatsapp-preview-adobe-express-entry-point");if(t)return t;await new Promise((t=>setTimeout(t,100)))}return null};updateWhatsappExpressState=async()=>{let t=await chrome.storage.local.get(this.whatsappExpressStateKey);t=t?.whatsappExpressState?t.whatsappExpressState:this.whatsappExpressInitialState;let e={...this.whatsappExpressInitialState,...t};e.fte.shown+=1,e.fte.lastShown=Date.now(),chrome.storage.local.set({[this.whatsappExpressStateKey]:e})};loadContentScripts=async()=>{const t=chrome.runtime.getURL("content_scripts/express/fte/express-contextual-fte.js");return Promise.all([import(t)]).then((t=>{this.expressContextualFteClass=t[0].default}))};isWhatsappDomain=()=>window.location.hostname.includes("web.whatsapp.com");init=async()=>{const t=await chrome.runtime.sendMessage({main_op:"whatsapp-express-init"});if(!this.isWhatsappDomain())return this.isEligible=async()=>!1,void(this.render=async()=>{});this.config=t,await this.loadContentScripts()}}