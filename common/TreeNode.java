package common;

import java.util.*;

/**
 * Definición estándar de LeetCode para árboles binarios.
 */
public class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;
    
    public TreeNode() {}
    public TreeNode(int val) { this.val = val; }
    public TreeNode(int val, TreeNode left, TreeNode right) {
        this.val = val;
        this.left = left;
        this.right = right;
    }

    @Override
    public String toString() {
        List<String> list = new ArrayList<>();
        Queue<TreeNode> queue = new LinkedList<>();
        queue.add(this);
        while (!queue.isEmpty()) {
            TreeNode curr = queue.poll();
            if (curr != null) {
                list.add(String.valueOf(curr.val));
                queue.add(curr.left);
                queue.add(curr.right);
            } else {
                list.add("null");
            }
        }
        // Eliminar 'null's sobrantes al final
        while (!list.isEmpty() && list.get(list.size() - 1).equals("null")) {
            list.remove(list.size() - 1);
        }
        return "[" + String.join(",", list) + "]";
    }
}
