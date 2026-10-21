import { JSDOM } from 'jsdom';
import { text } from 'stream/consumers';

function parseDocument(element) {
    function process_container(container,level){
        let elements=Array.from(container.childNodes)
            .map((child)=>flatten_node(child,level+1))
            .filter((text)=>text.length>0);
        return elements.join("\n\n");
    }

    function flatten_node(element,level){
        if(element.tagName){
            var tagName=element.tagName.toLowerCase();
        } else {
            var tagName=null;
        }

        if(element.nodeType==1 && tagName=="body"){
            return process_container(element,level);
        } else if (element.nodeType==1 && tagName=="div"){
            if (level==1 && element.classList.contains("footer-wikiwalk-nav")){
                return "";
            } else {
                return process_container(element,level);
            }
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="strong") {
            return "**"+process_container(element)+"**";
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="em") {
            return "*"+process_container(element)+"*";
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="p") {
            if(element.textContent.startsWith("[["))return "";
            let elements=Array.from(element.childNodes)
                .map((child)=>flatten_node(child,level+1))
                .filter((text)=>text.length>0);
            return elements.join("");
        } else if (element.nodeType==1 && tagName=="br"){
            if(element.parenttagName=="p") return "\n\n";
            else return "\u200c";
        } else if (element.nodeType==1 && tagName=="blockquote") {
            return "```\n"+process_container(element,level).trim()+"\n```";
        } else if (element.nodeType==3){
            return element.textContent;
        } else {
            return "";
        }
    }
    return flatten_node(element,0).trim();
}

async function main(){
    const html_data = await text(process.stdin);
    const dom = new JSDOM(html_data);
    const { window } = dom;
    const { document } = window;
    console.log(parseDocument(document.body));
}
main();
