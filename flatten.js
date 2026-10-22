import { JSDOM } from 'jsdom';
import { text } from 'stream/consumers';

function filter_modules(html){
    const regex=/\[\[(.*?)\]\]/g;
    const result = html.replace(regex, (_, module_text) => {
        if(module_text.startsWith("include")){
            module_text=module_text.slice(8).replaceAll("<br>","\n");
            let blocks=module_text.split("|").map((s)=>s.trim());
            let module_id=blocks[0];
            let args={};
            blocks.slice(1).forEach(block => {
                let [left, right]=block.split("=");
                args[left.trim()]=right.trim();
            });
            if(module_id.startsWith(":")){
                module_id=module_id.slice(module_id.slice(1).indexOf(":")+2); // strip namespace
            }
            switch(module_id){
                case "component:object-warning-box-source":
                    return "<strong>"+args["text-top"]+"</strong><br>"+args["text-bottom"]+"<br>"+args["object-number"];
            }
        }
        return "";
    });
    return result;
}

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
        } else if (element.nodeType==1 && tagName=="strong") {
            return "**"+process_container(element)+"**";
        } else if (element.nodeType==1 && tagName=="em") {
            return "*"+process_container(element)+"*";
        } else if (element.nodeType==1 && (tagName=="p"||tagName=="span")) {
            let elements=Array.from(element.childNodes);
            return elements.map((child)=>flatten_node(child,level+1))
                .filter((text)=>text.length>0)
                .join("");
        } else if (element.nodeType==1 && tagName=="br"){
            let parentTagName=element.parentElement.tagName.toLowerCase();
            if(parentTagName=="p"||parentTagName=="span") return "\n\n";
            else return "\u200c";
        } else if (element.nodeType==1 && tagName=="blockquote") {
            return "```\n"+process_container(element,level).trim()+"\n```";
        } else if (element.nodeType==1 && (tagName=="wj-footnote-ref-marker"||tagName=="sup")){
            return "<sup>"+process_container(element,level)+"</sup>";
        } else if (element.nodeType==1 && tagName=="sub"){
            return "<sub>"+process_container(element,level)+"</sub>";
        } else if (element.nodeType==1 && (tagName=="ol"||tagName=="ul")){
            return process_container(element,level);
        } else if (element.nodeType==1 && tagName=="li"){
            if(element.parentElement.tagName.toLowerCase()=="ol"){
                return element.getAttribute("data-id")+". "+process_container(element,level);
            } else {
                return "* "+process_container(element,level);
            }
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
    const clean_html=filter_modules(html_data);
    const dom = new JSDOM(clean_html);
    const { window } = dom;
    const { document } = window;
    console.log(parseDocument(document.body));
}
main();
