/**
 * 首页的例题。都是 render/examples 里审核过的场景，在线上预先生成好，点开就是现成的讲解页。
 * id 是线上任务号，还没生成的例题 id 留空，首页不显示。缩略图放在 public/examples。
 */
export interface Example {
  id: string;
  topic: string;
  length: string;
  text: string;
  image: string;
}

const ALL: Example[] = [
  {
    id: "35c6978092803fcc7f82c9ea6b1664f4",
    topic: "滑轮组",
    length: "0:59",
    text: "用滑轮组将重 240 N 的物体在 10 s 内匀速提升 2 m，求有用功、功率、机械效率和动滑轮重。",
    image: "/examples/pulley_n3.jpg",
  },
  {
    id: "6d998b970e23611c9be7274b4b131b93",
    topic: "浮力",
    length: "0:56",
    text: "弹簧测力计挂着圆柱体缓慢浸入水中，求浮力、圆柱体密度和下表面受到的压强。",
    image: "/examples/buoyancy.jpg",
  },
  {
    id: "7b2553bcb302cc0403044c178bfbb7de",
    topic: "斜面",
    length: "0:45",
    text: "沿斜面把 500 N 的物体匀速拉到顶端，求有用功、功率、机械效率和摩擦力。",
    image: "/examples/incline.jpg",
  },
  {
    id: "d25214679d78908fea58bee44acd3e3c",
    topic: "杠杆",
    length: "0:51",
    text: "杠杆一端挂 30 N 的物体，求平衡时的动力，再把物体撬高 0.1 m，求动力做的功。",
    image: "/examples/lever.jpg",
  },
];

export const EXAMPLES = ALL.filter((example) => example.id);
