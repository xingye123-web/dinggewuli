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
    id: "18558d3d76bd8be66bfb5f14a6ae5092",
    topic: "滑轮组",
    length: "1:42",
    text: "用滑轮组将重 240 N 的物体在 10 s 内匀速提升 2 m，求有用功、功率、机械效率和动滑轮重。",
    image: "/examples/pulley_n3.jpg",
  },
  {
    id: "13d346704e164697e8337db7ba698420",
    topic: "浮力",
    length: "1:48",
    text: "弹簧测力计挂着圆柱体缓慢浸入水中，求浮力、圆柱体密度和下表面受到的压强。",
    image: "/examples/buoyancy.jpg",
  },
  {
    id: "b9322ec765131ab70fa978efe5b8e8e4",
    topic: "斜面",
    length: "1:26",
    text: "沿斜面把 500 N 的物体匀速拉到顶端，求有用功、功率、机械效率和摩擦力。",
    image: "/examples/incline.jpg",
  },
  {
    id: "6c552731efd1b41616d891a6f98dd314",
    topic: "杠杆",
    length: "1:36",
    text: "杠杆一端挂 30 N 的物体，求平衡时的动力，再把物体撬高 0.1 m，求动力做的功。",
    image: "/examples/lever.jpg",
  },
];

export const EXAMPLES = ALL.filter((example) => example.id);
