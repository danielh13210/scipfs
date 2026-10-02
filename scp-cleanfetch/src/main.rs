use serde::{Deserialize, Serialize};
use ftml::render::Render;


// 1. Mirror the GraphQL JSON response structure into Rust Structs
#[derive(Deserialize, Debug)]
struct GraphQLResponse {
    data: DataContainer,
}

#[derive(Deserialize, Debug)]
struct DataContainer {
    page: PageContainer,
}

#[derive(Deserialize, Debug)]
struct PageContainer {
    #[serde(rename = "wikidotInfo")]
    wikidot_info: WikidotInfo,
}

#[derive(Deserialize, Debug)]
struct WikidotInfo {
    #[serde(rename = "createdAt")]
    created_at: String,
    title: String,
    source: String,
}

// 2. Define the payload structure we need to POST to Crom
#[derive(Serialize)]
struct GraphQLPayload {
    query: String,
}

fn wikitext_to_html(info: &WikidotInfo) -> String{
    let scp_id=&info.title;
    let page_info=ftml::data::PageInfo {
        title: scp_id.to_uppercase().into(),
        alt_title: None,
        site: "scp-wiki.wikidot.com".into(),
        page: ("/".to_string()+&scp_id.to_lowercase()).into(),
        tags: vec!["scp".into()],
        language: "en".into(),
        score: ftml::data::ScoreValue::Integer(1),
        category: None
    };
    let settings=ftml::settings::WikitextSettings{
        mode: ftml::settings::WikitextMode::Page,
        layout: ftml::layout::Layout::Wikijump,
        enable_page_syntax: false,
        use_true_ids: true,
        isolate_user_ids: false,
        minify_css: false,
        allow_local_paths: false,
        interwiki: ftml::settings::InterwikiSettings::new()
    };
    let mut source=info.source.clone();
    ftml::preproc::preprocess(&mut source);
    let tokenization=ftml::tokenizer::tokenize(&source);
    let parse_results=ftml::parsing::parse(&tokenization,&page_info,&settings);
    let renderer=ftml::render::html::HtmlRender{};
    let html=renderer.render(parse_results.value(),&page_info,&settings);
    return html.body;
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();

    let args: Vec<String> = std::env::args().collect();
    let arg1 = &args[1];
    // Define the query string exactly as before
    let raw_query = format!(r#"
        query TheCreationDate {{
          page(url: "http://scp-wiki.wikidot.com/{}") {{
            wikidotInfo {{
              createdAt
              title
              source
            }}
          }}
        }}
    "#,arg1).to_string();

    let payload = GraphQLPayload { query: raw_query };

    // 3. Make the async POST request with the Content-Type header and JSON payload
    // separate objects for debugging purposes
    let res1 = client
        .post("https://apiv1.crom.avn.sh/graphql")
        .header("Content-Type", "application/json")
        .header("User-Agent", "scp-cleanfetch/0.0.1")
        .json(&payload)
        .send()
        .await?;
//    println!("{}",(res1).text().await?);
    let res = res1
        .json::<GraphQLResponse>() // Deserialize straight into our structs
        .await?;

    let info = res.data.page.wikidot_info;

    // 4. Feed the raw source text natively into ftml
    println!("{}",wikitext_to_html(&info));
    println!("..CREATION: {}",info.created_at);

    Ok(())
}
