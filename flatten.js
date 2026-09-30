function parseDocument(element) {
    function process_container(container,level){
        elements=Array.from(container.childNodes)
            .map((child)=>flatten_node(child,level+1))
            .filter((text)=>text.length>0);
        return elements.join("\n\n");
    }

    function flatten_node(element,level){
        if(element.nodeType==1 && element.tagName.toLowerCase()=="div"){
            if(level==1 && 
                (element.querySelector(":scope > div.page-rate-widget-box") || 
                 element.classList.contains("footer-wikiwalk-nav") || 
                 element.classList.contains("licensebox"))){
                return "";
            } else {
                return process_container(element,level);
            }
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="strong") {
            return "**"+process_container(element)+"**";
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="em") {
            return "*"+process_container(element)+"*";
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="p") {
            elements=Array.from(element.childNodes)
                .map((child)=>flatten_node(child,level+1))
                .filter((text)=>text.length>0);
            return elements.join("");
        } else if (element.nodeType==1 && element.tagName.toLowerCase()=="blockquote") {
            return "```\n"+process_container(element).trim()+"\n```";
        } else if (element.nodeType==3){
            return element.textContent;
        } else {
            return "";
        }
    }
    return flatten_node(element,0).trim();
}