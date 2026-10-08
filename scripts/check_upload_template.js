// Run using playwright-cli run-code after selecting board_meeting and consent.
async (page) => {
  await page.unrouteAll({behavior:"ignoreErrors"});
  await page.goto("http://localhost:3210");
  await page.getByRole("tab",{name:/การประชุมบอร์ดบริหาร/}).click();
  await page.getByRole("checkbox").check();
  const id = "00000000-0000-4000-8000-000000000001";
  let created;
  await page.route("**/api/media", async route => {
    if (route.request().method() !== "POST") return route.continue();
    created = route.request().postDataJSON();
    await route.fulfill({json:{media_id:id,upload:{method:"PUT",url:"http://localhost:8210/api/upload/template-check"}}});
  });
  await page.route("**/api/upload/template-check", route=>route.fulfill({json:{ok:true}}));
  await page.route("**/api/media/"+id+"**", route=>{
    const path = route.request().url().split("?")[0];
    let json = {id,filename:"template-check.wav",status:"queued",summary_template:"board_meeting"};
    if(path.endsWith("/segments")||path.endsWith("/summaries"))json=[];
    if(path.endsWith("/start"))json={status:"queued"};
    return route.fulfill({json});
  });
  await page.locator("#audio-file").evaluate(input=>{
    const transfer=new DataTransfer();
    transfer.items.add(new File(["test audio fixture"],"template-check.wav",{type:"audio/wav"}));
    input.files=transfer.files;
    input.dispatchEvent(new Event("change",{bubbles:true}));
  });
  await page.waitForURL("**/media/"+id);
  await page.getByRole("tab",{name:/การประชุมบอร์ดบริหาร/}).waitFor();
  if(created?.summary_template!=="board_meeting")throw new Error("Wrong create-media template: "+JSON.stringify(created));
  if(await page.getByRole("tab",{name:/การประชุมบอร์ดบริหาร/}).getAttribute("aria-selected")!=="true")throw new Error("Saved template not selected on detail page");
  return {passed:true,postedTemplate:created.summary_template,detailSelection:"board_meeting",backend:"mocked upload, no cloud calls"};
}
