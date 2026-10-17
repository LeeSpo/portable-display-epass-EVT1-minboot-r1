#include <vector>
#include <queue>
#include <cmath>
#include <limits>
#include <algorithm>
extern "C" int astar(int nx,int ny,int nl,const unsigned char* block,const unsigned char* viaok,int start,int goal,int* output,int cap){
 int plane=nx*ny,N=plane*nl; const double INF=1e30;
 std::vector<double> dist(N,INF);std::vector<int> prev(N,-1);
 using V=std::pair<double,int>;std::priority_queue<V,std::vector<V>,std::greater<V>>Q;
 int gx=goal%nx,gy=(goal/ nx)%ny,gl=goal/plane;
 auto h=[&](int u){int x=u%nx,y=(u/nx)%ny,l=u/plane;return std::hypot(x-gx,y-gy)+(l==gl?0.:80.);};
 dist[start]=0;Q.push({h(start),start});int visited=0;
 while(!Q.empty()){
  auto [score,u]=Q.top();Q.pop();if(score>dist[u]+h(u)+1e-6)continue;
  if(u==goal){std::vector<int>p;for(int v=u;v!=-1;v=prev[v])p.push_back(v);if((int)p.size()>cap)return -2;std::reverse(p.begin(),p.end());for(int i=0;i<(int)p.size();i++)output[i]=p[i];return p.size();}
  if(++visited>4000000)return -3;
  int x=u%nx,y=(u/nx)%ny,l=u/plane;
  for(int dx=-1;dx<=1;dx++)for(int dy=-1;dy<=1;dy++){
   if(!dx&&!dy)continue;int xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=nx||yy>=ny)continue;
   int v=l*plane+yy*nx+xx;if(block[v])continue;
   if(dx&&dy&&(block[l*plane+y*nx+xx]||block[l*plane+yy*nx+x]))continue;
   double nd=dist[u]+(dx&&dy?1.4142135623730951:1.)+(l==2?.008:0.);
   if(nd<dist[v]-1e-7){dist[v]=nd;prev[v]=u;Q.push({nd+h(v),v});}
  }
  if(viaok[y*nx+x])for(int ll=0;ll<nl;ll++)if(ll!=l){int v=ll*plane+y*nx+x;if(!block[v]){double nd=dist[u]+80.;if(nd<dist[v]){dist[v]=nd;prev[v]=u;Q.push({nd+h(v),v});}}}
 }
 return -1;
}
